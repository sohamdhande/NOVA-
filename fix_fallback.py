import re

with open("controller.py", "r") as f:
    content = f.read()

# Append helper method at the end of Controller class.
# We'll just put it before the CONFIRMATION WORKFLOW line.

helper = """
    def _fallback_chat(self, command: str) -> dict:
        from llm import generate_summary
        prompt = f\"\"\"You are N.O.V.A, an AI assistant like JARVIS.
Be precise, efficient, mission-focused.
Keep responses concise and operational.
Never say 'Command not recognized'.

User: {command}\"\"\"
        try:
            resp = generate_summary(prompt)
        except Exception:
            resp = "Systems offline."
        
        return {
            "intent": "conversation",
            "domain": "system",
            "action": "chat",
            "risk": "low",
            "status": "success",
            "response": resp
        }

    # ================================================================
    # CONFIRMATION WORKFLOW
"""

content = content.replace("    # ================================================================\n    # CONFIRMATION WORKFLOW", helper)

# Now find all instances of standard error dicts.
# They look like:
# return {
#     "intent": "...",
#     "domain": "...",
#     "action": "...",
#     "risk": "...",
#     "status": "...",
#     "response": "Command not recognized."
# }
# and replace the `return {...}` with `return self._fallback_chat(command)`

# We'll do a regex replacement for the return dicts that contain "Command not recognized."
pattern = r"return\s+\{[\s\S]*?\"response\":\s*\"Command not recognized\.\"[\s\S]*?\}"
content = re.sub(pattern, "return self._fallback_chat(command)", content)

# Also replace the log response
content = content.replace('response="Command not recognized."', 'response="Redirected to conversation fallback."')

with open("controller.py", "w") as f:
    f.write(content)

print("Fixed controller.py")
