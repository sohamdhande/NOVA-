import os
import sys

# Add root folder to sys.path if not there so we can import llm
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from llm import _chat, MODEL_FAST, MODEL_LARGE

SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills")
SKILL_REGISTRY = {}

def scan_skills():
    """Scan the skills/ directory and build the registry map."""
    SKILL_REGISTRY.clear()
    if not os.path.exists(SKILLS_DIR):
        return
        
    for item in os.listdir(SKILLS_DIR):
        item_path = os.path.join(SKILLS_DIR, item)
        if os.path.isdir(item_path):
            skill_md_path = os.path.join(item_path, "SKILL.md")
            if os.path.exists(skill_md_path):
                # The folder name is the skill name
                SKILL_REGISTRY[item] = skill_md_path

def load_skill(skill_name: str) -> str:
    """Read and return the contents of a SKILL.md file."""
    if skill_name not in SKILL_REGISTRY:
        return ""
    try:
        with open(SKILL_REGISTRY[skill_name], "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"[skill_loader] Failed to read {skill_name}: {e}")
        return ""

def detect_skill(user_input: str) -> str | None:
    """Determine which skill is most relevant, or return None."""
    if not SKILL_REGISTRY:
        scan_skills()
        
    if not SKILL_REGISTRY:
        return None

    skill_names = ", ".join(SKILL_REGISTRY.keys())
    
    system_prompt = f"""You are a skill router. Given a user command and a list of available skills, return ONLY the name of the most relevant skill as a single word.
If no skill matches, return 'none'.
Available skills: {skill_names}"""

    try:
        response = _chat(
            system=system_prompt,
            user=user_input,
            model=MODEL_FAST,
            temperature=0.0
        ).strip().lower()
        
        # Clean up any surrounding punctuation or quotes
        response = ''.join(c for c in response if c.isalnum() or c == '_')
        
        if response in SKILL_REGISTRY:
            return response
            
        return None
    except Exception as e:
        print(f"[skill_loader] Router LLM failed: {e}")
        return None

def run_with_skill(user_input: str) -> str | None:
    """Route input to a skill. If matched, returns string execution results. If none, returns None."""
    matched_skill = detect_skill(user_input)
    if not matched_skill:
        return None
        
    # Load skill context
    skill_content = load_skill(matched_skill)
    if not skill_content:
        return None
        
    print(f"[skill_loader] Routing via skill: {matched_skill}")
    
    try:
        result = _chat(
            system=skill_content,
            user=user_input,
            model=MODEL_LARGE,
            temperature=0.2
        ).strip()
        return result
    except Exception as e:
        print(f"[skill_loader] Execution LLM failed: {e}")
        return None

# Initialize registry on import
scan_skills()
