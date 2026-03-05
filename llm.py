import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"

SYSTEM_PROMPT = """
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


BRIEFING_TEMPLATE = """You are NOVA.

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

Only output the briefing. No extra commentary.

---------------------------------------
CURRENT DATE:
{current_date}

CALENDAR EVENTS:
{calendar_events}

OPEN TASKS:
{open_tasks}

---------------------------------------"""


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
        current_date=date_str,
        calendar_events=events_block,
        open_tasks=tasks_block
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

        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
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

# --- PLAN CORRECTION ENGINE ---

CORRECTION_PROMPT = """You are the Plan Correction Engine.
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
Output: {"intent": "read", "steps": [{"domain": "calendar", "action": "read_today", "risk": "low"}]}
"""

def correct_plan(invalid_plan, errors):
    """Attempt to fix an invalid plan using LLM."""
    prompt = CORRECTION_PROMPT + f"\nINVALID PLAN:\n{json.dumps(invalid_plan)}\n\nERRORS:\n{json.dumps(errors)}\n"
    
    try:
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1},
            "format": "json"
        }
        response = requests.post(OLLAMA_URL, json=payload)
        return response.json()["response"]
    except:
        return {"status": "uncorrectable"}


# --- MEMORY AGENT ---

MEMORY_PROMPT = """You are the Memory Agent.
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
Output: {"action": "none"}
"""

def analyze_memory_intent(user_input):
    """Determine if input is memory-related."""
    prompt = MEMORY_PROMPT + f"\nUser Input: {user_input}\n"
    try:
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1},
            "format": "json"
        }
        res = requests.post(OLLAMA_URL, json=payload)
        return json.loads(res.json()["response"])
    except:
        return {"action": "none"}


# --- FOLDER WATCHER ---

FOLDER_WATCHER_PROMPT = """You are the Folder Watcher Agent.
Analyze the file context and decide what to do with it.

CONTEXT:
File Name: {file_name}
File Type: {file_type}
Extracted Text (if any): {extracted_text}

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
}
"""

def analyze_file_action(context):
    """Determine action for a new file."""
    prompt = FOLDER_WATCHER_PROMPT.format(**context)
    try:
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1},
            "format": "json"
        }
        res = requests.post(OLLAMA_URL, json=payload)
        return json.loads(res.json()["response"])
    except:
        return {"action": "ignore"}
