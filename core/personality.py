import os

# Personality state file path
STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills", "personality", "current.txt"
)

PERSONALITIES = {
    "jarvis": {
        "name": "JARVIS",
        "system_prefix": """You are NOVA, operating in JARVIS mode.
Tone: calm, precise, highly intelligent, slightly formal.
Like Tony Stark's AI — confident, efficient, never wastes words.
Address the user as 'Boss' occasionally.
Never say 'I am an AI'. Never apologize unnecessarily.
Get to the point immediately."""
    },
    "chill": {
        "name": "Chill",
        "system_prefix": """You are NOVA, operating in chill mode.
Tone: casual, friendly, like a smart friend texting you.
Use simple language. Occasional humor is fine.
No corporate speak. No unnecessary formality."""
    },
    "mentor": {
        "name": "Mentor",
        "system_prefix": """You are NOVA, operating in mentor mode.
Tone: patient, educational, encouraging.
Break things down clearly. Ask questions to help the user think.
Like a senior engineer guiding a junior one."""
    },
    "ghost": {
        "name": "Ghost",
        "system_prefix": """You are NOVA, operating in ghost mode.
Tone: ultra minimal. No fluff. No greetings. No explanations unless asked.
Output only what is needed. Maximum 2 sentences per response."""
    }
}

def get_personality() -> dict:
    """Read current.txt and return the matching PERSONALITIES entry."""
    mode = "jarvis"
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                content = f.read().strip().lower()
                if content in PERSONALITIES:
                    mode = content
    except Exception:
        pass
    
    return PERSONALITIES[mode]

def set_personality(mode: str) -> str:
    """Validate mode, write to current.txt, and return confirmation."""
    mode = mode.lower()
    if mode not in PERSONALITIES:
        return f"Unknown personality mode: {mode}. Valid modes are: {', '.join(PERSONALITIES.keys())}"
    
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f:
            f.write(mode)
        
        name = PERSONALITIES[mode]["name"]
        if mode == "jarvis":
            return f"Switching to {name} mode, Boss."
        else:
            return f"Switched personality to {name} mode."
    except Exception as e:
        return f"Failed to switch personality: {str(e)}"

def get_system_prefix() -> str:
    """Return the system_prefix of current personality."""
    persona = get_personality()
    return persona["system_prefix"] + "\n\nAlways format your responses using markdown. Use **bold** for important terms, ## headers for sections, - bullet points for lists, and `code` for technical terms. Make responses visually structured and scannable."
