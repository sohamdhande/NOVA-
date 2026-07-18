from dotenv import load_dotenv
load_dotenv()

import json
import os
from datetime import datetime

from groq import Groq, APIError, RateLimitError, APIStatusError

# ---------------------------------------------------------------------------
# Client setup — primary + fallback
# ---------------------------------------------------------------------------

_primary = Groq(api_key=os.getenv("GROQ_API_KEY_PRIMARY"))
_fallback = Groq(api_key=os.getenv("GROQ_API_KEY_FALLBACK"))

MODEL_LARGE = os.getenv("GROQ_MODEL_LARGE", "llama-3.1-8b-instant")   # planning, briefing
MODEL_FAST  = os.getenv("GROQ_MODEL_FAST",  "llama-3.1-8b-instant")      # memory, correction, subtasks

def _mask_key_str(key: str) -> str:
    if not key:
        return "empty"
    if len(key) > 8:
        return f"{key[:4]}***{key[-4:]}"
    elif len(key) > 4:
        return f"{key[:2]}***{key[-2:]}"
    return "***"


def _chat(
    system: str,
    user: str,
    *,
    model: str = MODEL_LARGE,
    temperature: float = 0.2,
    json_mode: bool = False,
) -> str:
    """
    Core completion call with automatic primary → fallback failover.
    Returns the raw content string.
    """
    kwargs: dict = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    client_candidates = [
        (_primary, "GROQ_API_KEY_PRIMARY", "PRIMARY"),
        (_fallback, "GROQ_API_KEY_FALLBACK", "FALLBACK")
    ]
    for idx, (cached_client, env_var, label) in enumerate(client_candidates):
        key_val = os.getenv(env_var, "")
        client = Groq(api_key=key_val) if key_val else cached_client
        if not client:
            continue
        try:
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except (RateLimitError, APIError, APIStatusError) as e:
            masked = _mask_key_str(key_val)
            key_desc = f"{label} [env: {env_var}, key: {masked}]"
            if idx < len(client_candidates) - 1:
                print(f"[llm] Key {key_desc} failed ({type(e).__name__}: {e}), switching to fallback...")
                continue
            print(f"[llm] Key {key_desc} also failed ({type(e).__name__}: {e})! All keys exhausted.")
            raise




# ===========================================================================
# SYSTEM PROMPTS  (unchanged from original)
# ===========================================================================

_PLAN_SYSTEM = """
You are NOVA's Task & Scheduling Orchestrator.

Your job is to convert user requests into structured execution plans
involving the following domains:

calendar
notion

You do NOT execute actions.
You ONLY generate a deterministic JSON plan.

-------------------------------------------------------
ARCHITECTURE RULES
-------------------------------------------------------

1. Planning ≠ Execution.
2. You must never generate conversational text.
3. Output JSON only.
4. Do not include explanations.
5. Do not invent tools.
6. Do not invent actions.
7. Never hallucinate data.
8. If required data must be fetched first, include a read step.
9. If mutation is required, mark it as high risk.

-------------------------------------------------------
ALLOWED DOMAINS & ACTIONS
-------------------------------------------------------

calendar:
  - read_today
  - read_range
  - create_event
  - update_event
  - delete_event

notion:
  - read_open
  - read_all
  - create_task
  - update_task

-------------------------------------------------------
RISK POLICY
-------------------------------------------------------

Low Risk:
- read_today
- read_range
- read_open
- read_all

High Risk:
- create_event
- update_event
- delete_event
- create_task
- update_task

High-risk actions must include:
"requires_confirmation": true

-------------------------------------------------------
PLANNING STRATEGY
-------------------------------------------------------

RULE 1:
If user intent depends on existing data,
you MUST fetch data first.

Example:
"Schedule review for unfinished tasks tomorrow"
→ Step 1: notion/read_open (low)
→ Step 2: calendar/create_event (high)

RULE 2:
Never create events without first determining:
- Title
- Date
- Start time
- End time

If user gives vague time like:
"tomorrow"
You must:
- Create a placeholder time block: 09:00–10:00 local
- Mark it clearly in parameters
- Execution layer may adjust later

RULE 3:
If user asks:
"What unfinished tasks do I have?"
→ Single step:
notion/read_open

RULE 4:
If user asks:
"Give me today's schedule"
→ Single step:
calendar/read_today

RULE 5:
If user asks to modify tasks based on calendar,
you must:
1. Fetch calendar
2. Fetch tasks
3. Perform reasoning step
4. Then apply updates

-------------------------------------------------------
OUTPUT FORMAT
-------------------------------------------------------

Always return:

{
  "intent": "<task|schedule|update|information>",
  "steps": [
    {
      "domain": "<calendar|notion>",
      "action": "<allowed_action>",
      "risk": "<low|high>",
      "parameters": { ... optional ... },
      "requires_confirmation": <true|false>
    }
  ]
}

Rules:
- Always use multi-step format.
- Even if only one step exists.
- Never include top-level domain/action.
- Never include "response".
- Never include commentary.

-------------------------------------------------------
TEMPORAL HANDLING RULES
-------------------------------------------------------

You are NOT allowed to compute calendar dates manually.

You must NOT:
- Convert relative dates into absolute dates.
- Perform time arithmetic.
- Guess timezones.
- Generate example dates like 2022-01-01.
- Hardcode ISO strings.

If the user provides:
- "tomorrow"
- "next week"
- "Friday at 3pm"
- "in 2 hours"
- "this afternoon"

You MUST return them in structured form using natural language fields.

When scheduling, use this structure inside parameters:

{
  "title": "...",
  "natural_datetime": "<exact phrase from user>",
  "duration_minutes": <default 60 if not specified>
}

Examples:

User: "Schedule review tomorrow at 3pm"

Output parameters:

{
  "title": "Review unfinished tasks",
  "natural_datetime": "tomorrow at 3pm",
  "duration_minutes": 60
}

User: "Block time next Monday afternoon"

Output:

{
  "title": "Focused work session",
  "natural_datetime": "next Monday afternoon",
  "duration_minutes": 60
}

CRITICAL:
You must preserve the original temporal phrase.
Do NOT convert to ISO format.
Do NOT fabricate exact times.
Do NOT guess dates.

The execution layer will handle deterministic date parsing.

-------------------------------------------------------
STRICT CONSTRAINT
-------------------------------------------------------

If unsure:
Choose safest possible read step first.

If user intent unclear:
Return single step:
calendar/read_today (low risk)

Never invent business context.
Never fabricate task titles.
Never assume meeting details.
Never create speculative content.

Return JSON only.

-------------------------------------------------------
STRICT OUTPUT RESTRICTIONS
-------------------------------------------------------

You are a planning module only.

You must NOT:
- Include execution results
- Include step_results
- Include current_step_index
- Include pending_steps
- Include all_steps
- Include response
- Include confirmation prompts
- Include execution state
- Include runtime metadata

The plan must contain exactly:

{
  "intent": "...",
  "steps": [...]
}

No additional top-level fields.
No execution data.
No partial state.
No runtime information.
"""

_BRIEFING_SYSTEM = """You are NOVA.

Generate a factual morning briefing using ONLY the data provided.

RULES:

1. Do NOT invent context.
2. Do NOT speculate.
3. Do NOT add advisory language.
4. Do NOT add motivational language.
5. Do NOT create conclusions beyond the data.
6. Do NOT contradict the provided data.
7. If tasks exist, do NOT say "no outstanding tasks."
8. If no tasks exist, explicitly say "No outstanding tasks."
9. If events exist, list them clearly.
10. If no events exist, state "No events scheduled today."
11. Keep under 200 words.
12. Keep tone concise and neutral.

FORMAT:

Morning Briefing — {current_date}

Calendar:
- List events OR state none.

Tasks:
- List tasks OR state none.

Workload:
- Light (0–2 items total)
- Moderate (3–5)
- Heavy (6+)

Conflicts:
- State clearly if none.
- If events overlap, mention conflict.

Only output the briefing. No extra commentary."""

_CORRECTION_SYSTEM = """You are the Plan Correction Engine.
Your goal is to fix JSON plans that failed validation using MINIMAL changes.

INPUT:
1. Original Invalid Plan (JSON)
2. Validation Errors (List of strings)

OUTPUT:
A Valid JSON Plan that fixes the errors.

STRICT RULES:
1. Do NOT change the user's intent.
2. Do NOT remove steps unless they are explicitly forbidden actions.
3. Do NOT add new steps.
4. Do NOT change domains.
5. Fix structure (e.g. wrap single steps in "steps" array).
6. Remove forbidden keys (e.g. "response").
7. Add missing required keys (e.g. "risk").
8. Ensure "domain" and "action" are allowed.

EXAMPLE:

Error: "Missing top-level key: steps"
Input: {"domain": "calendar", "action": "read"}
Output: {"intent": "read", "steps": [{"domain": "calendar", "action": "read_today", "risk": "low"}]}"""

_MEMORY_SYSTEM = """You are the Memory Agent.
Your job is to detect if the user wants to STORE, RECALL, or SEARCH information in long-term memory.

ACTIONS:
- store_entry: User wants to save/remember something.
- recall_topic: User wants to know about a specific topic.
- search_entries: User wants to find something vague.
- none: User is asking for a task/calendar action (not memory).

OUTPUT JSON:
{
  "action": "<store_entry|recall_topic|search_entries|none>",
  "topic": "...",     // Only for recall_topic. Must be a specific noun/subject. NO filler words.
  "data": {
    "title": "...",   // For store_entry
    "summary": "...", // For store_entry
    "tags": ["..."],  // For store_entry
    "query": "..."    // For search_entries
  }
}

RULES:
1. For recall_topic, "topic" MUST be the core subject only.
   - Bad: "what do i remember about nova architecture"
   - Good: "nova architecture"
   - Bad: "about project x"
   - Good: "project x"

2. Do NOT use "data" for recall_topic. Use top-level "topic" field.

3. IF NO SPECIFIC TOPIC IS MENTIONED:
   - Return {"action": "none"}
   - Do NOT guess a topic.
   - Do NOT use "memory" as a topic.
   - Do NOT use "everything" as a topic.

EXAMPLES:

User: "Remember that I like sushi."
Output: {"action": "store_entry", "data": {"title": "User Preference", "summary": "User likes sushi", "tags": ["preference", "food"]}}

User: "What do I know about Project X?"
Output: {"action": "recall_topic", "topic": "project x"}

User: "Recall facts about the python api"
Output: {"action": "recall_topic", "topic": "python api"}

User: "What do I remember?"
Output: {"action": "none"}

User: "Memory"
Output: {"action": "none"}

User: "Schedule a meeting"
Output: {"action": "none"}"""

_FOLDER_SYSTEM = """You are the Folder Watcher Agent.
Analyze the file context and decide what to do with it.

AVAILABLE ACTIONS:
- summarize_document (if file is PDF/TXT and needs reading)
- create_notion_entry (if file contains a task or actionable item)
- store_memory_entry (if file contains useful knowledge)
- ignore (if system file or irrelevant)

OUTPUT JSON:
{
  "action": "...",
  "data": {
    "title": "...",
    "content_summary": "...",
    "tags": [...]
  }
}"""

_SUBTASK_SYSTEM = """You are a task decomposition engine.
Break the given task into 3 to 6 concrete, actionable subtasks.
Each subtask must be a single clear action.
Return ONLY a JSON array of strings. No explanation. No markdown.
Example: ["Research options", "Draft outline", "Review with team"]"""


# ===========================================================================
# PUBLIC API  (same signatures as original)
# ===========================================================================

def generate_plan(user_input: str) -> str:
    """Convert a natural-language command into a JSON execution plan."""
    return _chat(
        system=_PLAN_SYSTEM,
        user=f"User Command: {user_input}",
        model=MODEL_LARGE,
        temperature=0.2,
        json_mode=True,
    )


def generate_summary(context: dict) -> str:
    """Turn structured context dict into a natural-language morning briefing."""
    date_str = datetime.now().strftime("%A, %B %d, %Y")

    events = context.get("events")
    events_block = (
        "\n".join(f"  {e['title']} — {e['start']}" for e in events)
        if events else "  No events scheduled."
    )

    tasks = context.get("tasks")
    tasks_block = (
        "\n".join(f"  [{t['status']}] {t['title']}" for t in tasks)
        if tasks else "  No open tasks."
    )

    # Fetch weather for morning briefing
    weather_line = ""
    weather = context.get("weather")
    if weather and isinstance(weather, dict):
        weather_line = f"Weather: {weather.get('temp')}°C, {weather.get('condition')}, {weather.get('humidity')}% humidity\n\n"
    else:
        try:
            import asyncio
            from tools.weather_tool import get_weather
            weather = asyncio.get_event_loop().run_until_complete(get_weather("Pune"))
            weather_line = (
                f"Weather: {weather['temp']}°C, {weather['condition']}, {weather['humidity']}% humidity\n\n"
            )
        except Exception:
            weather_line = "  Weather data unavailable."

    user_msg = (
        f"CURRENT DATE:\n{date_str}\n\n"
        f"WEATHER:\n{weather_line}\n\n"
        f"CALENDAR EVENTS:\n{events_block}\n\n"
        f"OPEN TASKS:\n{tasks_block}"
    )

    try:
        raw_summary = _chat(
            system=_BRIEFING_SYSTEM.format(current_date=date_str),
            user=user_msg,
            model=MODEL_LARGE,
            temperature=0.3,
        ).strip()
        
        # Prepend weather line if it doesn't already exist in the output
        if weather_line and "Weather:" not in raw_summary:
            return weather_line + raw_summary
        return raw_summary

    except Exception:
        # Deterministic fallback when both keys fail
        parts = [f"Briefing for {date_str}."]
        if weather_line:
            parts.append(weather_line.strip())
        if events:
            parts.append(f"Today's schedule: {', '.join(e['title'] for e in events)}.")
        else:
            parts.append("Calendar is clear.")
        if tasks:
            parts.append(f"Open tasks: {', '.join(t['title'] for t in tasks[:5])}.")
        else:
            parts.append("No pending tasks.")
        return " ".join(parts)


def correct_plan(invalid_plan: dict, errors: list) -> dict:
    """Attempt to fix an invalid plan using LLM."""
    user_msg = (
        f"INVALID PLAN:\n{json.dumps(invalid_plan)}\n\n"
        f"ERRORS:\n{json.dumps(errors)}"
    )
    try:
        raw = _chat(
            system=_CORRECTION_SYSTEM,
            user=user_msg,
            model=MODEL_FAST,
            temperature=0.1,
            json_mode=True,
        )
        return json.loads(raw)
    except Exception:
        return {"status": "uncorrectable"}


def analyze_memory_intent(user_input: str) -> dict:
    """Determine if input is memory-related."""
    try:
        raw = _chat(
            system=_MEMORY_SYSTEM,
            user=f"User Input: {user_input}",
            model=MODEL_FAST,
            temperature=0.1,
            json_mode=True,
        )
        return json.loads(raw)
    except Exception:
        return {"action": "none"}


def analyze_file_action(context: dict) -> dict:
    """Determine action for a new file."""
    user_msg = (
        f"File Name: {context.get('file_name')}\n"
        f"File Type: {context.get('file_type')}\n"
        f"Extracted Text (if any): {context.get('extracted_text')}"
    )
    try:
        raw = _chat(
            system=_FOLDER_SYSTEM,
            user=user_msg,
            model=MODEL_FAST,
            temperature=0.1,
            json_mode=True,
        )
        return json.loads(raw)
    except Exception:
        return {"action": "ignore"}


def generate_subtasks(task_title: str, priority: str = "medium", deadline: str = "") -> list[str]:
    """Break a task into 3-6 actionable subtasks using the LLM."""
    context_line = f"Priority: {priority}"
    if deadline:
        context_line += f", Deadline: {deadline}"

    user_msg = f'Task: "{task_title}"\n{context_line}'

    try:
        raw = _chat(
            system=_SUBTASK_SYSTEM,
            user=user_msg,
            model=MODEL_FAST,
            temperature=0.3,
            json_mode=True,
        )
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(s) for s in parsed[:6]]
        if isinstance(parsed, dict):
            for v in parsed.values():
                if isinstance(v, list):
                    return [str(s) for s in v[:6]]
        return []
    except Exception:
        print("[llm] Subtask generation failed — check API keys or retry.")
        return []