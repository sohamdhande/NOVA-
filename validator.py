
from datetime import datetime

ALLOWED_DOMAINS = {
    "calendar", "notion", "system", "pdf", "memory"
}

ALLOWED_ACTIONS = {
    "calendar": {
        "read_today", "read_range", "create_event", "update_event", "delete_event"
    },
    "notion": {
        "read_open", "read_all", "create_task", "update_task"
    },
    "system": {
        "morning_briefing"
    },
    "pdf": { # Legacy support until system fully transitioned
        "summarize" 
    },
    "memory": set() 
}

HIGH_RISK_ACTIONS = {
    "create_event", "update_event", "delete_event",
    "create_task", "update_task"
}

REQUIRED_PARAMS = {
    "create_event": ["title", "natural_datetime"],
    "update_event": ["title", "natural_datetime"]
}

def validate_iso8601(date_string):
    """Check if string is strict ISO 8601."""
    try:
        # Simple check for T separator and format
        datetime.fromisoformat(date_string)
        return True
    except (ValueError, TypeError):
        return False

def validate_step(step, step_index):
    """Validate a single execution step."""
    errors = []
    
    # 1. Required keys
    if not all(k in step for k in ("domain", "action", "risk")):
        return [f"Step {step_index}: Missing required keys (domain, action, risk)"]

    domain = step["domain"]
    action = step["action"]
    risk = step["risk"]
    
    # 2. Domain validation
    if domain not in ALLOWED_DOMAINS:
        errors.append(f"Step {step_index}: Unknown domain '{domain}'")
        return errors # Stop further validation for this step if domain is wrong

    # 3. Action validation
    # Allow unknown actions for pdf/memory currently as they are stubs/legacy
    if domain in ("calendar", "notion", "system"):
        if action not in ALLOWED_ACTIONS.get(domain, set()):
             errors.append(f"Step {step_index}: Action '{action}' not allowed for domain '{domain}'")

    # 4. Risk validation
    if action in HIGH_RISK_ACTIONS:
        if risk != "high":
            errors.append(f"Step {step_index}: Action '{action}' must be High Risk")
        if not step.get("requires_confirmation"):
            errors.append(f"Step {step_index}: High risk action '{action}' requires confirmation")
    elif risk == "high": # If marked high risk but not in list, still require confirmation
         if not step.get("requires_confirmation"):
             errors.append(f"Step {step_index}: High risk step requires confirmation")

    # 5. Parameter validation
    if action in REQUIRED_PARAMS:
        params = step.get("parameters", {})
        for req in REQUIRED_PARAMS[action]:
            if req not in params:
                 errors.append(f"Step {step_index}: Action '{action}' missing parameter '{req}'")
            # Note: We no longer enforce ISO 8601 for create/update event here
            # as they now use natural_datetime which is a free text string.
            # ISO validation is deferred to the execution layer if keys exist.
            if req == "start_datetime" or req == "end_datetime":
                 if not validate_iso8601(params[req]):
                     errors.append(f"Step {step_index}: Parameter '{req}' must be ISO 8601")

    # 6. Extra key check (simple version: check for 'response')
    if "response" in step:
         errors.append(f"Step {step_index}: Field 'response' is not allowed in plan")

    return errors

def validate_plan(plan):
    """Validate a full execution plan against strict rules.
    
    Returns:
        dict: {"status": "valid"} or {"status": "invalid", "errors": [...]}
    """
    if not isinstance(plan, dict):
         return {"status": "invalid", "errors": ["Plan must be a JSON object"]}

    errors = []

    # 1. Top-level structure
    if "intent" not in plan:
        errors.append("Missing top-level key: intent")
    if "steps" not in plan:
         errors.append("Missing top-level key: steps")
    elif not isinstance(plan["steps"], list):
         errors.append("Field 'steps' must be an array")
    
    if errors:
        return {"status": "invalid", "errors": errors}

    # 2. Step validation
    for i, step in enumerate(plan["steps"]):
        step_errors = validate_step(step, i + 1)
        errors.extend(step_errors)

    # 3. Forbidden keys
    if "response" in plan:
        errors.append("Field 'response' is not allowed in plan")
        
    if errors:
        return {"status": "invalid", "errors": errors}
        
    return {"status": "valid"}
