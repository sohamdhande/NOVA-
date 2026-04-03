import re

with open("core/intent_parser.py", "r") as f:
    text = f.read()

# 1. Replace import re
text = text.replace("import re\n", "import re as re_module\n", 1)

# 2. Replace re. methods globally
text = text.replace("re.search", "re_module.search")
text = text.replace("re.match", "re_module.match")
text = text.replace("re.IGNORECASE", "re_module.IGNORECASE")

# 3. Add NEWS and GMAIL blocks
blocks = """
        # ─── NEWS / INTELLIGENCE ──────────────────────────
        if any(p in msg for p in [
            "todays geopolitics", "intel briefing",
            "spy news", "intelligence briefing",
            "geopolitics news"
        ]):
            return ParsedIntent(
                intent="intel_briefing",
                tool="web",
                params={"query": msg},
                risk="LOW",
                raw_message=message
            )

        # ─── GMAIL ───────────────────────────────────────
        if any(p in msg for p in [
            "check my mails", "check my email",
            "summarize inbox", "my inbox",
            "check my inbox", "unread emails"
        ]):
            return ParsedIntent(
                intent="summarize_inbox",
                tool="gmail",
                params={},
                risk="LOW",
                raw_message=message
            )

        if msg.startswith("send email to ") or "send an email to" in msg:
            def parse_send_email(command: str) -> dict:
                pattern = r'send email to (.+?) subject (.+?) body (.+)'
                match = re_module.match(pattern, command.strip(), re_module.IGNORECASE)
                if match:
                    return {
                        "to": match.group(1).strip(),
                        "subject": match.group(2).strip(),
                        "body": match.group(3).strip()
                    }
                return {"raw": command}

            params = parse_send_email(message)
            return ParsedIntent(
                intent="send_email",
                tool="gmail",
                params=params,
                risk="MEDIUM",
                raw_message=message
            )

        # ─── WEBPAGE READING ─────────────────────────────"""

text = text.replace("        # ─── WEBPAGE READING ─────────────────────────────", blocks)

# 4. Inject LLM prompt updates for GMAIL
llm_examples = """
User: "check my inbox"
→ {"intent": "summarize_inbox", "tool": "gmail", "params": {}, "risk": "LOW"}

User: "send email to sohamdhande17@gmail.com subject test body hello"
→ {"intent": "send_email", "tool": "gmail", "params": {"to": "sohamdhande17@gmail.com subject test body hello", "raw": "send email to sohamdhande17@gmail.com subject test body hello"}, "risk": "MEDIUM"}

If unsure, default to intent="conversation", tool="llm" """

text = text.replace("If unsure, default to intent=\"conversation\", tool=\"llm\"", llm_examples)

# Fix duplicate WEBPAGE READING which was used as the anchor hook
text = text.replace("        # ─── WEBPAGE READING ─────────────────────────────\n\n        # ─── SCREENSHOTS", "        # ─── SCREENSHOTS")

with open("core/intent_parser.py", "w") as f:
    f.write(text)
print("Intent Parser Patched Successfully!")
