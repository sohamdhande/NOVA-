import json

REQUIRED_KEYS = {"intent", "domain", "action", "risk", "response"}
OPTIONAL_KEYS = {
    "file_path", "event_title", "start_datetime", "end_datetime",
    "task_title", "task_id", "task_status", "steps"
}

# Valid domains: pdf, calendar, task, notion, system, unknown
ALLOWED_KEYS = REQUIRED_KEYS | OPTIONAL_KEYS

# Required keys for each step in a multi-step plan
STEP_REQUIRED_KEYS = {"domain", "action", "risk"}


def validate_step(step):
    """Validate a single step object in a multi-step plan.

    Returns:
        True if step has all required keys, False otherwise.
    """
    if not isinstance(step, dict):
        return False
    return STEP_REQUIRED_KEYS.issubset(step.keys())


def validate_json(response_text):
    """Validate LLM JSON output.

    Supports two formats:
    1. Single-step: flat dict with required keys (backward compatible)
    2. Multi-step: flat dict with required keys + "steps" array

    Returns:
        Parsed dict if valid, None otherwise.
    """
    try:
        parsed = json.loads(response_text)

        if not REQUIRED_KEYS.issubset(parsed.keys()):
            return None

        # If steps are present, validate each one
        if "steps" in parsed:
            steps = parsed["steps"]
            if not isinstance(steps, list) or len(steps) == 0:
                return None
            for step in steps:
                if not validate_step(step):
                    return None

        return parsed

    except json.JSONDecodeError:
        return None
