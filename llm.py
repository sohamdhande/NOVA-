import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral:7b-instruct"

SYSTEM_PROMPT = """
You are NOVA — a strict, professional executive assistant.
Return JSON only. No explanations. No prose outside JSON.

ALLOWED DOMAINS: pdf, calendar, notion, system

CORE RULES:
- NEVER set "intent": "error" unless the request is truly impossible to fulfill.
- Do NOT claim an action has been completed. Only describe the intended action.
- Keep "response" short and professional.

SINGLE-DOMAIN RULES:
- pdf: include "file_path" (string or null).
- calendar read: intent "information", risk "low".
- calendar create: intent "task", risk "high". Extract "event_title", "start_datetime", "end_datetime" (ISO 8601). Default end = start + 1 hour.
- notion read: intent "information", action "read_tasks", risk "low".
- notion create: intent "task", action "create_task", risk "low". Extract "task_title".
- notion update: intent "task", action "update_task_status", risk "high". Extract "task_title", "task_status". Set "task_id" to null.
- system morning_briefing: intent "information", action "morning_briefing", risk "low".

MULTI-STEP RULES:
- If a command requires data from MULTIPLE domains, you MUST return a "steps" array.
- Each step: {"domain": "...", "action": "...", "parameters": {}, "risk": "low"|"high"}
- Steps execute sequentially. Order: reads before writes, low-risk before high-risk.
- When using "steps", set top-level "action" to "multi_step" and "domain" to the primary domain.
- If only one step is needed, you MAY use either the legacy flat format OR a single-element "steps" array.

CROSS-DOMAIN TRIGGERS (MUST use "steps"):
- "briefing of today", "daily summary", "summary of calendar + tasks"
- Any request combining calendar + notion + reasoning

DAILY BRIEFING OPTIONS:
Option A (single-step): domain "system", action "morning_briefing", risk "low"
Option B (multi-step):
  Step 1: {"domain": "calendar", "action": "read_today", "parameters": {}, "risk": "low"}
  Step 2: {"domain": "notion", "action": "read_open", "parameters": {}, "risk": "low"}
  Step 3: {"domain": "system", "action": "morning_briefing", "parameters": {}, "risk": "low"}

SINGLE-STEP SCHEMA:
{
  "intent": "information" | "task",
  "domain": "pdf" | "calendar" | "notion" | "system",
  "action": "string",
  "file_path": "string or null",
  "event_title": "string or null",
  "start_datetime": "ISO 8601 or null",
  "end_datetime": "ISO 8601 or null",
  "task_title": "string or null",
  "task_id": "string or null",
  "task_status": "string or null",
  "risk": "low" | "high",
  "response": "intended action description"
}

MULTI-STEP SCHEMA:
{
  "intent": "task",
  "domain": "primary domain",
  "action": "multi_step",
  "risk": "low" | "high",
  "response": "summary of all intended steps",
  "steps": [
    {"domain": "...", "action": "...", "parameters": {}, "risk": "low"},
    {"domain": "...", "action": "...", "parameters": {}, "risk": "high"}
  ]
}
"""


def generate_plan(user_input):
    prompt = SYSTEM_PROMPT + f"\nUser Command: {user_input}\n"

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }

    response = requests.post(OLLAMA_URL, json=payload)
    data = response.json()

    return data["response"]


BRIEFING_TEMPLATE = """You are an executive briefing officer. Deliver a morning briefing based on the data below.

Date: {date}

CALENDAR
{events_block}

OPEN TASKS
{tasks_block}

INSTRUCTIONS:
- 250 words max. No filler, no procedural language.
- Lead with the single most important thing today — a deadline, a conflict, or a high-stakes meeting.
- If any calendar events overlap in time, call that out directly.
- Group related items; do not list every item individually unless there are fewer than four.
- Prioritize tasks that appear urgent or blocked over routine ones.
- Close with one clear, actionable recommendation for the day.
- Tone: confident, direct, executive-level. Write as if speaking to a busy founder.
- Do NOT use bullet points excessively. Prefer short paragraphs.
- Do NOT say "here is your briefing" or "good morning" — start with substance."""


def generate_summary(context):
    """Turn structured context dict into a natural-language morning briefing.

    Args:
        context: dict with keys 'events' (list or None) and 'tasks' (list or None).

    Returns:
        str: A concise, executive-grade briefing string.
    """
    from datetime import datetime

    date_str = datetime.now().strftime("%A, %B %d, %Y")

    # Format events block
    events = context.get("events")
    if events:
        events_block = "\n".join(
            f"  {e['title']} — {e['start']}" for e in events
        )
    else:
        events_block = "  No events scheduled."

    # Format tasks block
    tasks = context.get("tasks")
    if tasks:
        tasks_block = "\n".join(
            f"  [{t['status']}] {t['title']}" for t in tasks
        )
    else:
        tasks_block = "  No open tasks."

    prompt = BRIEFING_TEMPLATE.format(
        date=date_str,
        events_block=events_block,
        tasks_block=tasks_block
    )

    try:
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3
            }
        }

        response = requests.post(OLLAMA_URL, json=payload)
        data = response.json()
        return data["response"].strip()

    except Exception:
        # Deterministic fallback when LLM is unreachable
        parts = [f"Briefing for {date_str}."]
        if events:
            names = ", ".join(e["title"] for e in events)
            parts.append(f"Today's schedule: {names}.")
        else:
            parts.append("Calendar is clear.")
        if tasks:
            names = ", ".join(t["title"] for t in tasks[:5])
            parts.append(f"Open tasks: {names}.")
        else:
            parts.append("No pending tasks.")
        return " ".join(parts)

