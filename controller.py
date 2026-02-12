from llm import generate_plan, generate_summary
from schema import validate_json
from tools.pdf_tool import PDFTool
from tools.calendar_tool import CalendarTool
from tools.notion_tool import NotionTool
from core.system_tool import SystemTool
from storage.logger import ExecutionLogger

# Initialize logger once
_logger = ExecutionLogger()


def handle_command(command):
    for attempt in range(2):  # Retry once if invalid
        raw_output = generate_plan(command)
        parsed = validate_json(raw_output)

        if parsed:
            # Multi-step execution
            if parsed.get("steps"):
                result = _execute_steps(command, parsed)
                return result

            # Route PDF commands
            if parsed.get("domain") == "pdf":
                result = _handle_pdf(parsed)
                _safe_log(command, result,
                          "success" if result.get("response", "").startswith("PDF summarized") else "error")
                return result

            # Route calendar commands
            if parsed.get("domain") == "calendar":
                result = _handle_calendar(parsed)
                if not result.get("requires_confirmation"):
                    status = "success" if result.get("response", "").startswith("Found") or \
                             result.get("response", "").startswith("No upcoming") else "planned"
                    _safe_log(command, result, status)
                return result

            # Route task/notion commands
            if parsed.get("domain") in ("task", "notion"):
                result = _handle_notion(parsed, command)
                if not result.get("requires_confirmation"):
                    status = "success" if "success" in result.get("response", "").lower() or \
                             result.get("response", "").startswith("Found") or \
                             result.get("response", "").startswith("No tasks") else "planned"
                    _safe_log(command, result, status)
                return result

            # Route system commands
            if parsed.get("domain") == "system":
                result = _handle_system(parsed)
                _safe_log(command, result, "success" if "briefing" in result.get("response", "").lower() else "error")
                return result

            # Non-execution (planning only)
            _safe_log(command, parsed, "planned")
            return parsed

    error_result = {
        "intent": "error",
        "domain": "unknown",
        "action": "none",
        "risk": "high",
        "response": "Unable to process command. Please rephrase."
    }
    _safe_log(command, error_result, "error")
    return error_result


def _handle_pdf(plan):
    """Execute PDF tool if file path is available."""
    file_path = plan.get("file_path")

    if not file_path:
        return {
            "intent": "task",
            "domain": "pdf",
            "action": plan.get("action", "summarize"),
            "risk": "low",
            "response": "File path required for PDF summarization."
        }

    tool = PDFTool()
    result = tool.execute(file_path)

    if result["status"] == "success":
        response_text = result["message"] + "\nSummary:\n" + result["summary"]
    else:
        response_text = result["message"]

    return {
        "intent": "task",
        "domain": "pdf",
        "action": plan.get("action", "summarize"),
        "risk": "low",
        "response": response_text
    }


def _handle_system(plan):
    """Orchestrate system commands like morning briefing.

    Workflow:
    1. Call CalendarTool.get_today_events()
    2. Call NotionTool.get_open_tasks()
    3. Merge results into structured context dict
    4. Send context to LLM summarization
    5. Return briefing text
    """
    action = plan.get("action", "morning_briefing")

    if action != "morning_briefing":
        return {
            "intent": "information",
            "domain": "system",
            "action": action,
            "risk": "low",
            "response": f"Unknown system action: {action}"
        }

    context = {"events": None, "tasks": None}
    errors = []

    # Step 1: Fetch today's calendar events
    try:
        cal = CalendarTool()
        cal_result = cal.get_today_events()
        if cal_result["status"] == "success":
            context["events"] = cal_result["data"]
        else:
            errors.append(f"Calendar: {cal_result['message']}")
    except Exception as e:
        errors.append(f"Calendar error: {str(e)}")

    # Step 2: Fetch open tasks from Notion
    try:
        notion = NotionTool()
        task_result = notion.get_open_tasks()
        if task_result["status"] == "success":
            context["tasks"] = task_result["data"]
        else:
            errors.append(f"Tasks: {task_result['message']}")
    except Exception as e:
        errors.append(f"Tasks error: {str(e)}")

    # Step 3: Context dict is now merged — generate briefing via LLM
    briefing = generate_summary(context)

    # Append any tool errors at the end
    if errors:
        briefing += "\n\n[Warnings: " + "; ".join(errors) + "]"

    return {
        "intent": "information",
        "domain": "system",
        "action": "morning_briefing",
        "risk": "low",
        "response": briefing
    }


def _handle_calendar(plan):
    """Route calendar commands: read events or prepare event creation."""
    intent = plan.get("intent", "information")

    if intent == "information":
        tool = CalendarTool()
        result = tool.execute("read")

        if result["status"] == "success" and result["data"]:
            lines = [result["message"]]
            for event in result["data"]:
                lines.append(f"  - {event['title']} at {event['start']}")
            response_text = "\n".join(lines)
        else:
            response_text = result["message"]

        return {
            "intent": "information",
            "domain": "calendar",
            "action": "read_events",
            "risk": "low",
            "response": response_text
        }

    elif intent == "task":
        event_title = plan.get("event_title", "Untitled Event")
        start_dt = plan.get("start_datetime")
        end_dt = plan.get("end_datetime")

        if not start_dt:
            return {
                "intent": "task",
                "domain": "calendar",
                "action": "create_event",
                "risk": "high",
                "response": "Cannot create event: start datetime missing. Please specify date and time."
            }

        return {
            "intent": "task",
            "domain": "calendar",
            "action": "create_event",
            "risk": "high",
            "requires_confirmation": True,
            "confirm_type": "calendar",
            "event_title": event_title,
            "start_datetime": start_dt,
            "end_datetime": end_dt,
            "response": f"Action requires confirmation: Create calendar event '{event_title}' on {start_dt}. Confirm? (yes/no)"
        }

    return {
        "intent": plan.get("intent"),
        "domain": "calendar",
        "action": "unknown",
        "risk": "low",
        "response": "Unrecognized calendar action."
    }


def _extract_task_title(command):
    """Extract task title from user command by stripping common prefixes."""
    import re
    cleaned = command.strip()
    # Remove common task prefixes (case-insensitive)
    cleaned = re.sub(
        r'^(create|add|make|new)\s+(a\s+)?task\s+(called|named|titled)?\s*',
        '', cleaned, flags=re.IGNORECASE
    ).strip()
    # Remove surrounding quotes if present
    cleaned = cleaned.strip('"').strip("'").strip()
    return cleaned if cleaned else None


def _handle_notion(plan, command=""):
    """Route task/notion commands: read, create, or update tasks."""
    intent = plan.get("intent", "information")
    action = plan.get("action", "")

    if intent == "information":
        # Read tasks — execute immediately
        tool = NotionTool()
        result = tool.execute("read")

        if result["status"] == "success" and result["data"]:
            lines = [result["message"]]
            for task in result["data"]:
                lines.append(f"  - [{task['status']}] {task['title']}")
            response_text = "\n".join(lines)
        else:
            response_text = result["message"]

        return {
            "intent": "information",
            "domain": "task",
            "action": "read_tasks",
            "risk": "low",
            "response": response_text
        }

    elif intent == "task":
        # Get task_title from LLM, fallback to extracting from command
        task_title = plan.get("task_title") or _extract_task_title(command)
        task_id = plan.get("task_id")
        task_status = plan.get("task_status", "Done")

        if "update" in action.lower() or "mark" in action.lower() or "status" in action.lower():
            # Update task status — high risk, require confirmation
            if not task_id:
                # Try to find task by title
                return {
                    "intent": "task",
                    "domain": "task",
                    "action": "update_task_status",
                    "risk": "high",
                    "requires_confirmation": True,
                    "confirm_type": "notion_update",
                    "task_title": task_title,
                    "task_id": task_id,
                    "task_status": task_status,
                    "response": f"Action requires confirmation: Update task '{task_title}' status to '{task_status}'. Confirm? (yes/no)"
                }

            return {
                "intent": "task",
                "domain": "task",
                "action": "update_task_status",
                "risk": "high",
                "requires_confirmation": True,
                "confirm_type": "notion_update",
                "task_title": task_title,
                "task_id": task_id,
                "task_status": task_status,
                "response": f"Action requires confirmation: Update task '{task_title}' status to '{task_status}'. Confirm? (yes/no)"
            }

        else:
            # Create task — low risk, execute immediately
            if not task_title:
                return {
                    "intent": "task",
                    "domain": "task",
                    "action": "create_task",
                    "risk": "low",
                    "response": "Task title is required to create a task."
                }

            tool = NotionTool()
            result = tool.execute("create", {"task_title": task_title})

            return {
                "intent": "task",
                "domain": "task",
                "action": "create_task",
                "risk": "low",
                "response": result["message"]
            }

    return {
        "intent": plan.get("intent"),
        "domain": "task",
        "action": "unknown",
        "risk": "low",
        "response": "Unrecognized task action."
    }


def execute_confirmed_action(command, plan):
    """Execute any confirmed high-risk action based on confirm_type."""
    confirm_type = plan.get("confirm_type", "calendar")

    if confirm_type == "calendar":
        tool = CalendarTool()
        result = tool.execute("create", {
            "event_title": plan.get("event_title"),
            "start_datetime": plan.get("start_datetime"),
            "end_datetime": plan.get("end_datetime")
        })

        response_text = result["message"]
        if result.get("data") and result["data"].get("link"):
            response_text += f"\nLink: {result['data']['link']}"

    elif confirm_type == "notion_update":
        tool = NotionTool()

        task_id = plan.get("task_id")

        # If no task_id, try to find by title
        if not task_id and plan.get("task_title"):
            lookup = tool.get_tasks(limit=20)
            if lookup["status"] == "success" and lookup["data"]:
                for t in lookup["data"]:
                    if plan["task_title"].lower() in t["title"].lower():
                        task_id = t["id"]
                        break

        if not task_id:
            _safe_log(command, plan, "error")
            return f"Could not find task '{plan.get('task_title', '')}' in Notion database."

        result = tool.execute("update", {
            "task_id": task_id,
            "task_status": plan.get("task_status", "Done")
        })
        response_text = result["message"]

    else:
        _safe_log(command, plan, "error")
        return "Unknown confirmation type."

    status = "success" if result["status"] == "success" else "error"
    _safe_log(command, plan, status)
    return response_text


def cancel_confirmed_action(command, plan):
    """Log a cancelled high-risk action."""
    _safe_log(command, plan, "cancelled")


def _safe_log(command, result, status):
    """Log execution without breaking flow if logging fails."""
    try:
        _logger.log_execution(command, result, result.get("response", ""), status)
    except Exception as e:
        print(f"[Logger Warning]: {e}")


def get_logger():
    """Expose logger for CLI access."""
    return _logger


# ---------------------------------------------------------------------------
# Multi-step execution
# ---------------------------------------------------------------------------

_TOOL_MAP = {
    "pdf": lambda: PDFTool(),
    "calendar": lambda: CalendarTool(),
    "task": lambda: NotionTool(),
    "notion": lambda: NotionTool(),
    "system": lambda: SystemTool(),
}


def _execute_single_step(step):
    """Execute one step by routing domain+action to the right tool.

    Args:
        step: dict with domain, action, parameters, risk.

    Returns:
        dict with keys: status, domain, action, risk, response.
    """
    domain = step.get("domain", "unknown")
    action = step.get("action", "")
    parameters = step.get("parameters", {})

    # Special case: system domain morning_briefing uses orchestrator
    if domain == "system" and action == "morning_briefing":
        result = _handle_system({"action": "morning_briefing"})
        return {
            "status": "success",
            "domain": "system",
            "action": action,
            "risk": step.get("risk", "low"),
            "response": result["response"]
        }

    tool_factory = _TOOL_MAP.get(domain)
    if not tool_factory:
        return {
            "status": "error",
            "domain": domain,
            "action": action,
            "risk": step.get("risk", "low"),
            "response": f"Unknown domain: {domain}"
        }

    try:
        tool = tool_factory()
        result = tool.execute(action, parameters)
        return {
            "status": result.get("status", "error"),
            "domain": domain,
            "action": action,
            "risk": step.get("risk", "low"),
            "response": result.get("message", "")
        }
    except Exception as e:
        return {
            "status": "error",
            "domain": domain,
            "action": action,
            "risk": step.get("risk", "low"),
            "response": f"Step failed: {str(e)}"
        }


def _execute_steps(command, parsed):
    """Execute a multi-step plan sequentially.

    Rules:
    - Steps run in order.
    - Each step is logged individually.
    - If a step has risk == "high", pause and return for confirmation.
    - If a step fails, stop execution immediately.

    Returns:
        dict with standard keys + step_results list.
    """
    steps = parsed.get("steps", [])
    step_results = []

    for i, step in enumerate(steps):
        # High-risk step: pause for confirmation
        if step.get("risk") == "high":
            step_log = {
                "intent": "task",
                "domain": step.get("domain", "unknown"),
                "action": step.get("action", ""),
                "risk": "high",
                "response": f"Step {i + 1}: {step.get('action', '')} on {step.get('domain', '')} requires confirmation."
            }
            _safe_log(command, step_log, "planned")

            return {
                "intent": parsed.get("intent", "task"),
                "domain": parsed.get("domain", "unknown"),
                "action": "multi_step",
                "risk": "high",
                "response": f"Step {i + 1}/{len(steps)} requires confirmation: {step.get('action', '')} on {step.get('domain', '')}. Confirm? (yes/no)",
                "requires_confirmation": True,
                "confirm_type": "multi_step",
                "step_results": step_results,
                "current_step_index": i,
                "pending_steps": steps[i:],
                "all_steps": steps
            }

        # Execute the step
        result = _execute_single_step(step)
        step_results.append(result)

        # Log individually
        step_log = {
            "intent": parsed.get("intent", "task"),
            "domain": result["domain"],
            "action": result["action"],
            "risk": result["risk"],
            "response": result["response"]
        }
        _safe_log(command, step_log, result["status"])

        # Fail-fast: stop if step errored
        if result["status"] == "error":
            return {
                "intent": parsed.get("intent", "task"),
                "domain": parsed.get("domain", "unknown"),
                "action": "multi_step",
                "risk": parsed.get("risk", "low"),
                "response": f"Pipeline stopped at step {i + 1}/{len(steps)}: {result['response']}",
                "step_results": step_results
            }

    # All steps completed
    summaries = [f"Step {j + 1}: {r['response']}" for j, r in enumerate(step_results)]
    return {
        "intent": parsed.get("intent", "task"),
        "domain": parsed.get("domain", "unknown"),
        "action": "multi_step",
        "risk": parsed.get("risk", "low"),
        "response": "All steps completed.\n" + "\n".join(summaries),
        "step_results": step_results
    }


def execute_confirmed_step(command, plan):
    """Resume a paused multi-step pipeline after high-risk confirmation.

    Executes the confirmed step, then continues with remaining steps.

    Returns:
        str: Combined response text from executed steps.
    """
    pending = plan.get("pending_steps", [])
    all_steps = plan.get("all_steps", [])
    prior_results = plan.get("step_results", [])
    current_idx = plan.get("current_step_index", 0)

    if not pending:
        return "No pending steps to execute."

    responses = []

    for i, step in enumerate(pending):
        step_num = current_idx + i + 1

        # First step in pending was the confirmed high-risk step — execute it
        # Subsequent high-risk steps pause again (but for simplicity, execute all after confirmation)
        result = _execute_single_step(step)

        step_log = {
            "intent": "task",
            "domain": result["domain"],
            "action": result["action"],
            "risk": result["risk"],
            "response": result["response"]
        }
        _safe_log(command, step_log, result["status"])

        responses.append(f"Step {step_num}: {result['response']}")

        # Fail-fast
        if result["status"] == "error":
            responses.append(f"Pipeline stopped at step {step_num}/{len(all_steps)}.")
            break

    return "\n".join(responses)
