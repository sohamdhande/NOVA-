"""
NOVA Chat Engine — Structured tactical response layer.

Sits between the API endpoint and the Controller/HealthEngine/ContextEngine.
Parses user messages, detects special modes (simulation, context lock),
routes commands, adapts tone by health zone, and returns structured responses.
"""

import re
import logging
from datetime import datetime
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Client-handled commands (validated here, rendered on frontend)       #
# ------------------------------------------------------------------ #

CLIENT_COMMANDS = {
    "open tasks":    {"action": "navigate", "target": "tasks"},
    "open finance":  {"action": "navigate", "target": "finance"},
    "clear":         {"action": "clear_chat"},
    "tactical mode": {"action": "set_mode", "mode": "tactical"},
    "strategic mode": {"action": "set_mode", "mode": "strategic"},
}

LOCK_PATTERN = re.compile(r"^lock\s+context\s+(.+)$", re.IGNORECASE)
UNLOCK_PATTERN = re.compile(r"^unlock\s+context$", re.IGNORECASE)
SIMULATE_PATTERN = re.compile(r"^simulate\s+(.+)$", re.IGNORECASE)

# ------------------------------------------------------------------ #
#  Tone Templates                                                      #
# ------------------------------------------------------------------ #

_TONE_PREFIX = {
    "stable":     "",
    "controlled": "",
    "elevated":   "",
    "critical":   "",
}

_TONE_SUFFIX = {
    "stable":     "",
    "controlled": "",
    "elevated":   "",
    "critical":   "",
}


def _apply_tone(message: str, zone: str) -> str:
    """Adapt response message to current health zone."""
    if zone == "stable":
        return message
    elif zone == "controlled":
        return message
    elif zone == "elevated":
        # Prefix tactical urgency
        if not message.startswith("ALERT"):
            return message
        return message
    else:  # critical
        # Prefix urgency marker
        if not message.upper().startswith("CRITICAL"):
            return message
        return message


def _tone_wrap(raw_response: str, zone: str, domain: str = "") -> str:
    """
    Rewrite controller response for zone-appropriate tone.
    Deterministic — no randomness.
    """
    if zone == "stable":
        return f"System stable. {raw_response}"
    elif zone == "controlled":
        return f"{raw_response}"
    elif zone == "elevated":
        return f"Attention required. {raw_response}"
    else:  # critical
        return f"{raw_response} Immediate action required."


# ------------------------------------------------------------------ #
#  Structured Block Builders                                           #
# ------------------------------------------------------------------ #


def _build_task_list_block(controller_result: Dict) -> Optional[Dict]:
    """Extract task list from controller response if applicable."""
    domain = controller_result.get("domain", "")
    action = controller_result.get("action", "")

    if domain in ("notion", "task") and action in ("read_open", "read_tasks"):
        response = controller_result.get("response", "")
        items = []
        for line in response.split("\n"):
            stripped = line.strip()
            if stripped.startswith("-") or stripped.startswith("•"):
                items.append(stripped.lstrip("-•").strip())
        if items:
            return {"type": "task_list", "items": items}

    # Also check step_results for multi-step
    for sr in controller_result.get("step_results", []):
        block = _build_task_list_block(sr)
        if block:
            return block

    return None


def _build_finance_block(controller_result: Dict) -> Optional[Dict]:
    """Extract finance summary if applicable."""
    domain = controller_result.get("domain", "")
    if domain != "expense":
        return None
    # Placeholder — expense tool doesn't go through controller yet
    return None


def _build_advisory_block(context_eval: Dict) -> Optional[Dict]:
    """Wrap proactive advisory as structured block."""
    if not context_eval or not context_eval.get("triggered"):
        return None
    payload = context_eval.get("payload")
    if not payload:
        return None
    return {
        "type": "advisory",
        "recommendations": payload.get("recommendations", []),
    }


# ------------------------------------------------------------------ #
#  ChatEngine                                                          #
# ------------------------------------------------------------------ #


class ChatEngine:
    """
    Structured chat routing engine.

    Responsibilities:
      - Parse message → detect simulation / context lock / client command
      - Route to Controller for complex commands
      - Wrap response with tone, structured blocks, projection
      - Decide compact vs expanded mode
    """

    def __init__(self, controller, health_engine, context_engine):
        self.controller = controller
        self.health_engine = health_engine
        self.context_engine = context_engine
        self._context_lock: Optional[str] = None  # locked section name

    # -------------------------------------------------------------- #
    #  Public API                                                      #
    # -------------------------------------------------------------- #

    def handle_message(self, message: str, session_id: str = None,
                       current_health_data: Dict = None,
                       current_metrics: Dict = None) -> Dict:
        """
        Main entry point.

        Returns:
            {
                status: str,
                trace: list[str],
                message: str,
                structured: dict | None,
                projection: dict | None,
                response_mode: str,
            }
        """
        message = message.strip()
        trace: List[str] = []
        zone = (current_health_data or {}).get("health_zone", "stable")
        current_health = (current_health_data or {}).get("system_health", 100)

        if not message:
            return self._build_response(
                status="info",
                message="No input received.",
                trace=["empty_input"],
                zone=zone,
            )

        trace.append(f"input_received: {message[:60]}")

        # ---- 1. Context Lock Commands ----
        lock_match = LOCK_PATTERN.match(message)
        if lock_match:
            section = lock_match.group(1).strip()
            self._context_lock = section
            trace.append(f"context_locked: {section}")
            return self._build_response(
                status="success",
                message=f"Context locked to: {section}.",
                trace=trace,
                zone=zone,
            )

        if UNLOCK_PATTERN.match(message):
            prev = self._context_lock
            self._context_lock = None
            trace.append(f"context_unlocked: {prev}")
            return self._build_response(
                status="success",
                message="Context unlocked.",
                trace=trace,
                zone=zone,
            )

        # ---- 2. Client-Handled Commands ----
        cmd_lower = message.lower().strip()
        if cmd_lower in CLIENT_COMMANDS:
            action_info = CLIENT_COMMANDS[cmd_lower]
            trace.append(f"client_command: {cmd_lower}")
            return self._build_response(
                status="success",
                message=f"Routing to client: {cmd_lower}.",
                trace=trace,
                zone=zone,
                structured={"type": "client_command", **action_info},
            )

        # ---- 3. Simulation Mode ----
        sim_match = SIMULATE_PATTERN.match(message)
        if sim_match:
            sim_command = sim_match.group(1).strip()
            trace.append(f"simulation_mode: {sim_command[:50]}")
            return self._handle_simulation(
                sim_command, trace, zone, current_health, current_metrics
            )

        # ---- 4. Route Through Controller ----
        trace.append("routing: controller")
        return self._handle_controller_command(
            message, trace, zone, current_health, current_metrics
        )

    # -------------------------------------------------------------- #
    #  Simulation                                                      #
    # -------------------------------------------------------------- #

    def _handle_simulation(self, command: str, trace: List[str],
                           zone: str, current_health: int,
                           current_metrics: Dict = None) -> Dict:
        """
        Dry-run: route through controller but do NOT execute mutations.
        Compute projected health using temporary raw calculation.
        """
        # Run controller in normal mode — it will plan but we only care about the plan
        # For a true dry-run we'd need controller support; for now we simulate
        # by computing what WOULD happen to health.
        trace.append("simulation: dry_run")

        # Compute projected health by simulating worse metrics
        projection = None
        if self.health_engine and current_metrics:
            projected_raw = self.health_engine._compute_raw_health(current_metrics)
            projected_smoothed = round(current_health * 0.75 + projected_raw * 0.25)
            projection = {
                "current_health": current_health,
                "projected_health": projected_smoothed,
            }
            trace.append(f"projected_health: {projected_smoothed}")

        return self._build_response(
            status="info",
            message=_tone_wrap(
                f"Simulation complete. No mutations executed. Projected health: {projection['projected_health'] if projection else 'N/A'}.",
                zone,
            ),
            trace=trace,
            zone=zone,
            projection=projection,
        )

    # -------------------------------------------------------------- #
    #  Controller Routing                                               #
    # -------------------------------------------------------------- #

    def _handle_controller_command(self, message: str, trace: List[str],
                                   zone: str, current_health: int,
                                   current_metrics: Dict = None) -> Dict:
        """Route through the existing Controller and wrap the result."""
        try:
            result = self.controller.handle_command(message)
        except Exception as e:
            logger.error(f"Controller error: {e}")
            trace.append(f"controller_error: {str(e)[:80]}")
            return self._build_response(
                status="warning",
                message="Command processing failed.",
                trace=trace,
                zone=zone,
            )

        ctrl_status = result.get("status", "error")
        ctrl_response = result.get("response", "")
        ctrl_domain = result.get("domain", "")
        ctrl_action = result.get("action", "")

        trace.append(f"controller_status: {ctrl_status}")
        trace.append(f"controller_domain: {ctrl_domain}/{ctrl_action}")

        # Map controller status → chat status
        if ctrl_status == "success":
            chat_status = "success"
        elif ctrl_status in ("rejected", "ignored"):
            chat_status = "info"
        elif result.get("requires_confirmation"):
            chat_status = "blocked"
            trace.append("blocked: requires_confirmation")
        else:
            chat_status = "warning"

        # Blocked by guardrail
        if ctrl_status == "blocked":
            chat_status = "blocked"
            trace.append("blocked: guardrail")

        # Apply tone
        toned_message = _tone_wrap(ctrl_response, zone, ctrl_domain)

        # Build structured blocks
        structured = _build_task_list_block(result)
        if not structured:
            structured = _build_finance_block(result)

        # Health projection (if mutation executed)
        projection = None
        is_mutation = ctrl_status == "success" and ctrl_action and (
            "create" in ctrl_action or "update" in ctrl_action or "store" in ctrl_action
        )
        if is_mutation and self.health_engine and current_metrics:
            trace.append("computing_health_projection")
            new_health_data = self.health_engine.calculate_health(current_metrics)
            projection = {
                "current_health": current_health,
                "projected_health": new_health_data.get("system_health", current_health),
            }

        # If confirmation required, include the confirmation data
        if result.get("requires_confirmation"):
            structured = {
                "type": "confirmation_required",
                "domain": ctrl_domain,
                "action": ctrl_action,
                "risk": result.get("risk", "high"),
            }

        return self._build_response(
            status=chat_status,
            message=toned_message,
            trace=trace,
            zone=zone,
            structured=structured,
            projection=projection,
        )

    # -------------------------------------------------------------- #
    #  Response Builder                                                 #
    # -------------------------------------------------------------- #

    def _build_response(self, status: str, message: str, trace: List[str],
                        zone: str, structured: Dict = None,
                        projection: Dict = None) -> Dict:
        """Assemble the final chat response dict."""
        # Decide response mode
        mode = self._decide_mode(trace, structured, projection)

        return {
            "status": status,
            "trace": trace,
            "message": message,
            "structured": structured,
            "projection": projection,
            "response_mode": mode,
        }

    @staticmethod
    def _decide_mode(trace: List[str], structured: Dict = None,
                     projection: Dict = None) -> str:
        """
        compact: short confirmation, single-line, no structured data.
        expanded: structured data, projection, ≥5 trace lines, advisory.
        """
        if structured is not None:
            return "expanded"
        if projection is not None:
            return "expanded"
        if len(trace) >= 5:
            return "expanded"
        return "compact"
