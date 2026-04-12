import sys
import os

# Add root folder to sys.path if not there so we can import llm
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from llm import _chat, MODEL_FAST

def needs_clarification(user_input: str, intent: dict) -> str | None:
    """Determine if a requested action is missing critical parameters needed for execution."""
    
    system_prompt = """You are NOVA's clarity checker. Given a user command and its parsed 
intent, determine if critical information is missing before execution.

Only ask if something is TRULY missing that would cause the action to fail.
Examples of when to ask:
- send email but no recipient → ask for recipient
- create event but no date → ask for date
- delete something but unclear what → ask for confirmation

Examples of when NOT to ask:
- read emails → no clarification needed
- today's news → no clarification needed

If clarification needed, return ONLY the question as a plain string.
If no clarification needed, return 'none'."""

    user_msg = f"User Request: {user_input}\nParsed Intent: {intent}"

    try:
        response = _chat(
            system=system_prompt,
            user=user_msg,
            model=MODEL_FAST,
            temperature=0.0
        ).strip()
        
        # We test for 'none' case-insensitively
        if response.lower().strip() == 'none':
            return None
            
        return response
    except Exception as e:
        print(f"[clarity_engine] LLM failed: {e}")
        return None
