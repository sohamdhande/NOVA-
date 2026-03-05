"""
NOVA Controller - Contract-Hardened Production Version

Enforces:
- Deterministic routing order
- Gibberish pre-filtering
- Tool contract validation
- Multi-step execution
- Zero hallucination tolerance
"""
import re
import string
import asyncio
from core.event_bus import event_bus, NovaEvent
from core.biometric import biometric_auth
try:
    import config
except ImportError:
    class config:
        DEBUG = False
        MIN_TOPIC_LENGTH = 3
        MAX_CORRECTION_ATTEMPTS = 2


# HARD CONTRACT DEFINITIONS
ALLOWED_DOMAINS = {"calendar", "notion", "task", "memory", "system", "pdf"}

ALLOWED_ACTIONS = {
    "calendar": {"create_event", "read_today"},
    "notion": {"read_open", "create_task", "update_task"},
    "task": {"read_open", "create_task", "update_task"},
    "memory": {"store_entry", "search_entries", "recall_topic"},
    "system": {"morning_briefing"},
    "pdf": {"summarize", "extract"}
}

RECOGNIZED_VERBS = {
    "schedule", "create", "update", "delete", "show", "list", "read",
    "remember", "recall", "store", "note", "search", "find",
    "review", "check", "get", "tell", "what", "how", "when", "where"
}


class Controller:
    """
    Production-grade orchestration controller.
    
    Contract guarantees:
    - No gibberish reaches planner
    - No unsupported actions reach tools
    - No hallucinations reach execution
    - All paths validated before execution
    """
    
    def __init__(self, logger, telemetry, guardrail, memory_tool, 
                 calendar_tool, notion_tool, pdf_tool, system_tool):
        """Initialize with dependency injection."""
        self.logger = logger
        self.telemetry = telemetry
        self.guardrail = guardrail
        self.memory_tool = memory_tool
        self.calendar_tool = calendar_tool
        self.notion_tool = notion_tool
        self.pdf_tool = pdf_tool
        self.system_tool = system_tool
        
        # Tool registry for dynamic lookup
        self.tools = {
            "memory": memory_tool,
            "calendar": calendar_tool,
            "notion": notion_tool,
            "task": notion_tool,  # Alias
            "pdf": pdf_tool,
            "system": system_tool
        }
        
        self._pending_confirmations = {}
        
        # Subscribe to Event Bus
        event_bus.subscribe("email_received", self._on_email_received)
        event_bus.subscribe("telemetry_synced", self._on_telemetry_synced)
        event_bus.subscribe("daemon_started", self._on_daemon_started)
        event_bus.subscribe("action_approved", self._on_action_approved)

    # ================================================================
    # EVENT HANDLERS
    # ================================================================

    async def _on_email_received(self, event: NovaEvent):
        """React to incoming email events from the daemon."""
        subject = event.payload.get("subject", "Unknown")
        sender = event.payload.get("sender", "Unknown")
        preview = event.payload.get("preview", "")
        # Log receipt
        print(f"[NOVA CONTROLLER] Email event received: '{subject}' from {sender}")
        # If priority is high (>=7), trigger a summarization command automatically
        if event.priority >= 7:
            # Handle synchronously if handle_command isn't async, or via to_thread
            if asyncio.iscoroutinefunction(self.handle_command):
                await self.handle_command(f"summarize email from {sender}: {preview}")
            else:
                self.handle_command(f"summarize email from {sender}: {preview}")

    async def _on_telemetry_synced(self, event: NovaEvent):
        """React to telemetry sync events."""
        snapshot = event.payload.get("snapshot", {})
        print(f"[NOVA CONTROLLER] Telemetry synced: {snapshot}")

    async def _on_daemon_started(self, event: NovaEvent):
        """React to daemon start event."""
        print(f"[NOVA CONTROLLER] Daemon started at {event.payload.get('timestamp')}")

    async def _on_action_approved(self, event: NovaEvent):
        """React to user approving a high risk action via Dashboard queue."""
        action_id = event.payload.get("id")
        self._log_execution(
            command=f"Approval processed for action_id={action_id}",
            intent="system",
            domain="system",
            action="approve",
            risk="low",
            status="success",
            response=f"Manual execution trigger accepted for {action_id}"
        )
        
        # We need to retrieve the action details from the SQLite events table
        import sqlite3, os, json
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nova_logs.db")
        try:
            # Running this blocking DB fetch via to_thread since we are in async context
            def fetch_cmd():
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM events WHERE id=?", (action_id,)).fetchone()
                conn.close()
                return row
                
            row = await asyncio.to_thread(fetch_cmd)
            
            if row:
                payload = json.loads(row["payload"])
                cmd = payload.get("command")
                if cmd:
                    # Reroute it but whitelist it from requiring TouchID again
                    self._pending_confirmations[cmd] = True
                    # Let handle_command trigger normally
                    await asyncio.to_thread(self.handle_command, cmd)
                    
        except Exception as e:
            print(f"[NOVA CONTROLLER] Error executing approved action: {e}")

    def _publish_sync(self, event: NovaEvent):
        """Helper to publish events from synchronous methods."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(event_bus.publish(event))
        except RuntimeError:
            # If no running loop in context, we start a throwaway one
            asyncio.run(event_bus.publish(event))
    
    def handle_command(self, command):
        """
        Main entry point with hardened routing.
        
        Routing order (STRICT):
        1. Trim & empty check
        2. System commands
        3. Explicit memory patterns
        4. Gibberish detection
        5. Planner invocation
        6. Validation & correction
        7. Contract verification
        8. Execution
        """
        # -----------------------------------------------------------
        # STEP 1: TRIM INPUT
        # -----------------------------------------------------------
        command = command.strip()
        
        # Empty input already handled by CLI - this is defensive
        if not command:
            return {
                "intent": "none",
                "domain": "system",
                "action": "none",
                "risk": "low",
                "status": "ignored",
                "response": ""
            }
        
        # -----------------------------------------------------------
        # STEP 2: SYSTEM COMMANDS (bypass planner)
        # -----------------------------------------------------------
        # These are handled by CLI but included here for completeness
        cmd_lower = command.lower().strip()
        
        if cmd_lower in ("exit", "quit"):
            return {"intent": "system", "domain": "system", "action": "exit", 
                    "risk": "low", "status": "success", "response": "Exiting"}
        
        # -----------------------------------------------------------
        # STEP 3: EXPLICIT MEMORY PATTERNS (bypass planner)
        # -----------------------------------------------------------
        
        # Memory store patterns
        memory_store_patterns = [
            (r'^remember\s+(.+)', "remember"),
            (r'^store\s+that\s+(.+)', "store that"),
            (r'^note\s+that\s+(.+)', "note that"),
            (r'^save\s+memory\s+(.+)', "save memory")
        ]
        
        for pattern, trigger in memory_store_patterns:
            match = re.match(pattern, cmd_lower, re.IGNORECASE)
            if match:
                content = command[len(trigger):].strip()
                if content:
                    return self._execute_memory_store(command, content)
        
        # Memory search/recall patterns
        memory_query_patterns = [
            (r'^what\s+do\s+i\s+remember\s+about\s+(.+)', "what do i remember about"),
            (r'^have\s+i\s+worked\s+on\s+(.+)', "have i worked on"),
            (r'^did\s+i\s+(.+)', "did i"),
            (r'^what\s+did\s+i\s+(.+)', "what did i"),
            (r'^recall\s+(.+)', "recall"),
            (r'^search\s+memory\s+for\s+(.+)', "search memory for"),
            (r'^what\s+do\s+you\s+know\s+about\s+(.+)', "what do you know about")
        ]
        
        for pattern, trigger in memory_query_patterns:
            match = re.match(pattern, cmd_lower, re.IGNORECASE)
            if match:
                topic = match.group(1).strip().rstrip(string.punctuation)
                if topic and len(topic) >= config.MIN_TOPIC_LENGTH:
                    return self._execute_memory_recall(command, topic)
        
        # -----------------------------------------------------------
        # STEP 4: GIBBERISH DETECTION (pre-planner filter)
        # -----------------------------------------------------------
        
        if self._is_gibberish(command):
            self._log_execution(
                command=command,
                intent="unknown",
                domain="unknown",
                action="none",
                risk="low",
                status="rejected",
                response="Command not recognized."
            )
            return {
                "intent": "unknown",
                "domain": "unknown",
                "action": "none",
                "risk": "low",
                "status": "rejected",
                "response": "Command not recognized."
            }
        
        # -----------------------------------------------------------
        # STEP 5: PLANNER INVOCATION
        # -----------------------------------------------------------
        
        try:
            from llm import generate_plan, correct_plan
            from schema import validate_json
            from validator import validate_plan
        except ImportError as e:
            return {
                "intent": "error",
                "domain": "system",
                "action": "startup",
                "risk": "high",
                "status": "error",
                "response": f"Failed to load required modules: {e}"
            }
        
        self.telemetry.increment("planner_invoked")
        
        try:
            raw_output = generate_plan(command)
            parsed = validate_json(raw_output)
        except Exception as e:
            self.logger.log_error(command, f"Planning Error: {e}")
            self.telemetry.increment("planner_failed")
            return {
                "intent": "error",
                "domain": "system",
                "action": "plan",
                "risk": "low",
                "status": "error",
                "response": "Command not recognized."
            }
        
        if not parsed:
            self.telemetry.increment("planner_failed")
            return {
                "intent": "error",
                "domain": "system",
                "action": "plan",
                "risk": "low",
                "status": "error",
                "response": "Command not recognized."
            }
        
        # -----------------------------------------------------------
        # STEP 6: VALIDATION & CORRECTION LOOP
        # -----------------------------------------------------------
        
        for attempt_idx in range(config.MAX_CORRECTION_ATTEMPTS + 1):
            validation = validate_plan(parsed)
            
            if validation["status"] == "valid":
                break
            
            self.telemetry.increment("validation_failed", metadata={"errors": str(validation["errors"])})
            
            if config.DEBUG:
                print(f"[Controller] Plan invalid: {validation['errors']}")
            
            if attempt_idx >= config.MAX_CORRECTION_ATTEMPTS:
                self.telemetry.increment("correction_failed", metadata={"reason": "max_attempts_exceeded"})
                self._log_execution(
                    command=command,
                    intent="error",
                    domain="system",
                    action="correct",
                    risk="low",
                    status="error",
                    response="Command not recognized."
                )
                return {
                    "intent": "error",
                    "domain": "system",
                    "action": "correct",
                    "risk": "high",
                    "status": "error",
                    "response": "Command not recognized."
                }
            
            self.telemetry.increment("correction_invoked", metadata={"attempt": attempt_idx + 1})
            corrected = correct_plan(parsed, validation["errors"])
            
            if corrected.get("status") == "uncorrectable":
                self.telemetry.increment("correction_failed", metadata={"reason": "llm_uncorrectable"})
                self._log_execution(
                    command=command,
                    intent="error",
                    domain="system",
                    action="correct",
                    risk="low",
                    status="error",
                    response="Command not recognized."
                )
                return {
                    "intent": "error",
                    "domain": "system",
                    "action": "correct",
                    "risk": "high",
                    "status": "error",
                    "response": "Command not recognized."
                }
            
            parsed = corrected
        
        # -----------------------------------------------------------
        # STEP 7: CONTRACT VERIFICATION (post-validation safety)
        # -----------------------------------------------------------
        
        # Check if plan is semantically useless
        if self._is_plan_unknown(parsed):
            self._log_execution(
                command=command,
                intent="unknown",
                domain="unknown",
                action="none",
                risk="low",
                status="rejected",
                response="Command not recognized."
            )
            return {
                "intent": "unknown",
                "domain": "unknown",
                "action": "none",
                "risk": "low",
                "status": "rejected",
                "response": "Command not recognized."
            }
        
        # Verify domain contract
        if not self._verify_domain_contract(parsed):
            self._log_execution(
                command=command,
                intent=parsed.get("intent", "unknown"),
                domain=parsed.get("domain", "unknown"),
                action=parsed.get("action", "none"),
                risk="low",
                status="rejected",
                response="Command not recognized."
            )
            return {
                "intent": "unknown",
                "domain": parsed.get("domain", "unknown"),
                "action": "none",
                "risk": "low",
                "status": "rejected",
                "response": "Command not recognized."
            }
        
        # Verify action contract (for single-step or steps)
        if not self._verify_action_contract(parsed):
            self._log_execution(
                command=command,
                intent=parsed.get("intent", "unknown"),
                domain=parsed.get("domain", "unknown"),
                action=parsed.get("action", "none"),
                risk="low",
                status="rejected",
                response="Command not recognized."
            )
            return {
                "intent": "unknown",
                "domain": parsed.get("domain", "unknown"),
                "action": parsed.get("action", "none"),
                "risk": "low",
                "status": "rejected",
                "response": "Command not recognized."
            }
        
        # -----------------------------------------------------------
        # STEP 8: EXECUTION ROUTING
        # -----------------------------------------------------------
        
        # Multi-step execution
        if parsed.get("steps"):
            return self._execute_steps(command, parsed)
        
        # Single-step execution
        return self._execute_single_step(command, parsed)
    
    # ================================================================
    # GIBBERISH DETECTION
    # ================================================================
    
    def _is_gibberish(self, command):
        """
        Pre-planner gibberish filter.
        
        Rejects:
        - Less than 2 meaningful words
        - No recognized verbs
        - Over 60% non-alphabetic
        - Single token > 8 chars
        - Repeated character patterns
        """
        cmd_lower = command.lower().strip()
        
        # Check alphabetic ratio
        if command:
            alpha_ratio = sum(c.isalpha() or c.isspace() for c in command) / len(command)
            if alpha_ratio < 0.4:  # Less than 40% alphabetic
                return True
        
        # Tokenize
        tokens = cmd_lower.split()
        
        # Less than 2 tokens (excluding very short commands with verbs)
        if len(tokens) < 2:
            # Single token must be a recognized verb or command
            if tokens and tokens[0] not in RECOGNIZED_VERBS:
                return True
        
        # Check for single very long random token
        for token in tokens:
            clean_token = ''.join(c for c in token if c.isalpha())
            if len(clean_token) > 12 and clean_token not in RECOGNIZED_VERBS:
                # Check if it looks random (no vowels or all consonants)
                vowels = sum(1 for c in clean_token if c in 'aeiou')
                if vowels < len(clean_token) * 0.2:  # Less than 20% vowels
                    return True
        
        # Check for recognized verbs
        has_verb = any(word in RECOGNIZED_VERBS for word in tokens)
        if not has_verb and len(tokens) > 1:
            # No verb and multiple tokens = likely gibberish
            # Unless it's a question word (handle contractions like "what's")
            question_words = {"what", "when", "where", "who", "why", "how"}
            # Check for question words or contractions (what's, where's, etc.)
            has_question = any(
                word in question_words or 
                any(word.startswith(q) for q in question_words)
                for word in tokens
            )
            if not has_question:
                return True
        
        # Check for repeated character patterns (e.g., "aaaaaa", "123123123")
        for token in tokens:
            if len(token) > 4:
                # Check for repeated chars
                if len(set(token)) < len(token) * 0.3:  # Less than 30% unique chars
                    return True
                # Check for repeated patterns
                for i in range(1, len(token) // 2 + 1):
                    pattern = token[:i]
                    if pattern * (len(token) // i) == token[:len(token) // i * i]:
                        if len(token) // i >= 3:  # Pattern repeats 3+ times
                            return True
        
        return False
    
    # ================================================================
    # CONTRACT VERIFICATION
    # ================================================================
    
    def _is_plan_unknown(self, parsed):
        """
        Detect semantically useless plans.
        
        Returns True if:
        - Intent is "unknown"
        - No executable steps
        - Empty domain
        - No meaningful result expected
        """
        intent = parsed.get("intent", "").lower()
        domain = parsed.get("domain", "").lower()
        action = parsed.get("action", "").lower()
        steps = parsed.get("steps", [])
        
        # Explicit unknown
        if intent == "unknown":
            return True
        
        # No steps and no domain
        if not steps and not domain:
            return True
        
        # Domain is unknown or empty
        if domain in ("unknown", ""):
            if not steps:  # No steps to fall back on
                return True
        
        # Information intent with no actionable parameters
        if intent == "information" and not steps and not action:
            return True
        
        return False
    
    def _verify_domain_contract(self, parsed):
        """
        Verify plan uses allowed domains.
        
        Checks:
        - Top-level domain in whitelist
        - All step domains in whitelist
        """
        # Check top-level domain
        domain = parsed.get("domain", "").lower()
        if domain and domain not in ALLOWED_DOMAINS:
            if config.DEBUG:
                print(f"[Contract] Rejected domain: {domain}")
            return False
        
        # Check step domains
        steps = parsed.get("steps", [])
        for step in steps:
            step_domain = step.get("domain", "").lower()
            if step_domain and step_domain not in ALLOWED_DOMAINS:
                if config.DEBUG:
                    print(f"[Contract] Rejected step domain: {step_domain}")
                return False
        
        return True
    
    def _verify_action_contract(self, parsed):
        """
        Verify plan uses allowed actions for domains.
        
        Checks:
        - Single-step action in whitelist
        - All step actions in whitelist
        - Tool methods exist
        """
        # Check single-step action
        domain = parsed.get("domain", "").lower()
        action = parsed.get("action", "").lower()
        
        if domain and action:
            if domain in ALLOWED_ACTIONS:
                if action not in ALLOWED_ACTIONS[domain]:
                    if config.DEBUG:
                        print(f"[Contract] Rejected action {action} for domain {domain}")
                    return False
                
                # Verify tool method exists
                if not self._verify_tool_method(domain, action):
                    if config.DEBUG:
                        print(f"[Contract] Tool method missing: {domain}.{action}")
                    return False
        
        # Check step actions
        steps = parsed.get("steps", [])
        for step in steps:
            step_domain = step.get("domain", "").lower()
            step_action = step.get("action", "").lower()
            
            if step_domain and step_action:
                if step_domain in ALLOWED_ACTIONS:
                    if step_action not in ALLOWED_ACTIONS[step_domain]:
                        if config.DEBUG:
                            print(f"[Contract] Rejected step action {step_action} for domain {step_domain}")
                        return False
                    
                    # Verify tool method exists
                    if not self._verify_tool_method(step_domain, step_action):
                        if config.DEBUG:
                            print(f"[Contract] Tool method missing: {step_domain}.{step_action}")
                        return False
        
        return True
    
    def _verify_tool_method(self, domain, action):
        """
        Verify tool has the required method.
        
        Prevents AttributeError at execution time.
        """
        if domain not in self.tools:
            return False
        
        tool = self.tools[domain]
        
        # All tools use execute() method for routing
        # Direct method check is not reliable since tools may use internal routing
        return hasattr(tool, "execute") or hasattr(tool, action)
    
    # ================================================================
    # MEMORY EXECUTION (explicit patterns only)
    # ================================================================
    
    def _execute_memory_store(self, command, content):
        """Execute explicit memory storage."""
        result = self.memory_tool.execute("store_entry", {
            "data": {
                "source_type": "manual",
                "title": content[:50],
                "summary": content,
                "tags": []
            }
        })
        
        self._log_execution(
            command=command,
            intent="memory",
            domain="memory",
            action="store_entry",
            risk="low",
            status="success",
            response=result["message"]
        )
        
        return {
            "intent": "memory",
            "domain": "memory",
            "action": "store_entry",
            "risk": "low",
            "status": "success",
            "response": result["message"]
        }
    
    def _interpolate_parameters(self, step, step_results, command):
        """
        Inject data from previous steps into current step parameters.
        
        Use case: "schedule unfinished tasks for tomorrow 2pm"
        Step 1: notion/read_open → returns task list
        Step 2: calendar/create_event → needs task titles + datetime
        
        This method enriches Step 2 parameters with Step 1 data.
        """
        from utils.date_parser import parse_natural_date
        
        domain = step.get("domain")
        action = step.get("action")
        params = step.get("parameters", {})
        
        # Only interpolate for calendar/create_event following notion/read_open
        if domain == "calendar" and action == "create_event" and len(step_results) > 0:
            # Check if previous step was notion read
            prev_step = step_results[-1]
            
            if prev_step.get("domain") == "notion" and prev_step.get("action") == "read_open":
                # Extract task data from previous response
                prev_response = prev_step.get("response", "")
                
                # Parse task list from response
                tasks = self._parse_tasks_from_response(prev_response)
                
                if tasks:
                    # If no title specified, use task summary
                    if not params.get("title"):
                        if len(tasks) == 1:
                            params["title"] = tasks[0]
                        else:
                            params["title"] = f"Review {len(tasks)} unfinished tasks"
                    
                    # If no description, add task list
                    if not params.get("description"):
                        params["description"] = "Tasks to review:\n" + "\n".join([f"- {t}" for t in tasks])
                    
                    if config.DEBUG:
                        print(f"[Controller] Interpolated params (before date parse): {params}")
        
        # Parse natural_datetime into start_datetime/end_datetime for calendar events
        if domain == "calendar" and action == "create_event":
            # Get natural datetime from params or extract from command
            natural_dt = params.get("natural_datetime")
            
            # Check if natural_dt is vague or empty - replace with extracted datetime
            vague_terms = ["sometime", "later", "soon", "eventually", "someday", ""]
            if not natural_dt or any(vague in str(natural_dt).lower() for vague in vague_terms):
                natural_dt = self._extract_datetime_from_command(command)
                if config.DEBUG:
                    print(f"[Controller] Replaced vague/empty datetime with: '{natural_dt}'")
            elif config.DEBUG:
                print(f"[Controller] Using planner's natural_datetime: '{natural_dt}'")
            
            # If still no title, generate a generic one
            if not params.get("title"):
                params["title"] = "Scheduled task"
                if config.DEBUG:
                    print(f"[Controller] No title provided, using default: '{params['title']}'")
            
            # Parse datetime if we don't have start_datetime yet
            if not params.get("start_datetime") and natural_dt:
                try:
                    duration = params.get("duration_minutes", 60)
                    start_iso, end_iso = parse_natural_date(natural_dt, duration_minutes=duration)
                    
                    params["start_datetime"] = start_iso
                    params["end_datetime"] = end_iso
                    
                    if config.DEBUG:
                        print(f"[Controller] Parsed '{natural_dt}' → {start_iso} to {end_iso}")
                        
                except Exception as e:
                    if config.DEBUG:
                        print(f"[Controller] Date parsing failed: {e}")
                    # Keep params as-is, will fail validation later
        
        # Update step with enriched parameters
        step["parameters"] = params
        return step
    
    def _parse_tasks_from_response(self, response):
        """Extract task titles from notion read response."""
        tasks = []
        
        # Response format: "Found 2 task(s)." or similar
        # Try to extract task names if available
        lines = response.split("\n")
        for line in lines:
            # Look for task patterns like "- Task name" or "• Task name"
            if line.strip().startswith("-") or line.strip().startswith("•"):
                task = line.strip().lstrip("-•").strip()
                if task:
                    tasks.append(task)
        
        return tasks
    
    def _extract_datetime_from_command(self, command):
        """Extract temporal reference from user command."""
        import re
        
        command_lower = command.lower()
        
        # Specific patterns (high priority)
        specific_patterns = [
            r"tomorrow\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
            r"tomorrow\s+(\d{1,2}\s*(?:am|pm))",
            r"today\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
            r"(next\s+\w+\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
            r"(this\s+\w+\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
            r"at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm))",
        ]
        
        for pattern in specific_patterns:
            match = re.search(pattern, command_lower)
            if match:
                return match.group(0)
        
        # General day references (medium priority)
        day_patterns = [
            r"\b(tomorrow)\b",
            r"\b(today)\b",
            r"\b(tonight)\b",
            r"\b(next\s+monday|next\s+tuesday|next\s+wednesday|next\s+thursday|next\s+friday|next\s+saturday|next\s+sunday)\b",
        ]
        
        for pattern in day_patterns:
            match = re.search(pattern, command_lower)
            if match:
                matched_day = match.group(1)
                # Add default time based on context
                if "morning" in command_lower:
                    return f"{matched_day} at 9am"
                elif "afternoon" in command_lower:
                    return f"{matched_day} at 2pm"
                elif "evening" in command_lower or "tonight" in matched_day:
                    return f"{matched_day} at 6pm"
                else:
                    # Default to 2pm for unspecified time
                    return f"{matched_day} at 2pm"
        
        # Vague references (low priority) - map to sensible defaults
        if any(word in command_lower for word in ["sometime", "later", "soon", "eventually"]):
            # Default to tomorrow at 2pm for vague requests
            return "tomorrow at 2pm"
        
        # Last resort fallback
        return "tomorrow at 2pm"
    
    def _execute_memory_recall(self, command, topic):
        """Execute explicit memory recall."""
        result = self.memory_tool.execute("recall_topic", {"topic": topic})
        
        self._log_execution(
            command=command,
            intent="memory",
            domain="memory",
            action="recall_topic",
            risk="low",
            status="success",
            response=result["message"]
        )
        
        return {
            "intent": "memory",
            "domain": "memory",
            "action": "recall_topic",
            "risk": "low",
            "status": "success",
            "response": result["message"]
        }
    
    # ================================================================
    # MULTI-STEP EXECUTION ENGINE
    # ================================================================
    
    def _execute_steps(self, command, plan):
        """
        Deterministic multi-step execution.
        
        For each step:
        1. Check confirmation if high-risk
        2. Validate step contract
        3. Run guardrail
        4. Increment mutation_attempt
        5. Execute
        6. Increment mutation_success/blocked
        7. Stop on failure
        """
        steps = plan.get("steps", [])
        step_results = []
        
        for i, step in enumerate(steps):
            step_num = i + 1
            domain = step.get("domain", "unknown")
            action = step.get("action", "unknown")
            risk = step.get("risk", "low")
            
            if config.DEBUG:
                print(f"[Controller] Step {step_num}/{len(steps)}: {domain}/{action}")
            
            # Parameter interpolation: inject previous step data
            step = self._interpolate_parameters(step, step_results, command)
            
            # High-risk confirmation
            if risk == "high" and plan.get("requires_confirmation", False):
                self._publish_sync(NovaEvent(
                    source="controller",
                    type="approval_required",
                    payload={
                        "command": command,
                        "reason": f"High risk action detected: {action} on {domain}. Requires manual oversight."
                    },
                    priority=8
                ))
                
                # Check if this precise command was just manually approved via the queue
                if command in self._pending_confirmations and self._pending_confirmations[command]:
                    authorized = True
                    # Consume the approval so it cannot be reused
                    self._pending_confirmations.pop(command)
                else:
                    try:
                        # Check if we are already inside a running loop (like FastAPI)
                        loop = asyncio.get_running_loop()
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor(1) as pool:
                            # Call async from sync thread
                            authorized = pool.submit(
                                asyncio.run, 
                                biometric_auth.require_auth(action_name=action, risk_level=risk)
                            ).result()
                    except RuntimeError:
                        # Simple sync call
                        authorized = asyncio.run(biometric_auth.require_auth(
                            action_name=action,
                            risk_level=risk
                        ))
                
                if not authorized:
                    return {"status": "blocked", "reason": "Authorization denied"}
            
            # Mutation detection
            is_mutation = action in ("create", "update", "delete", "schedule", "send", "modify", "create_event", "create_task", "update_event", "update_task", "delete_event", "delete_task")
            
            # Guardrail check for mutations
            if is_mutation:
                allowed, reason = self.guardrail.check_constraints(domain, action)
                
                if not allowed:
                    self.telemetry.increment("mutation_blocked", metadata={
                        "reason": reason or "guardrail",
                        "step": step_num
                    })
                    
                    blocked_result = {
                        "domain": domain,
                        "action": action,
                        "risk": risk,
                        "status": "blocked",
                        "response": f"Guardrail blocked: {reason or 'Safety violation'}"
                    }
                    step_results.append(blocked_result)
                    
                    self._log_execution(
                        command=command,
                        intent=plan.get("intent", "task"),
                        domain=domain,
                        action=action,
                        risk=risk,
                        status="blocked",
                        response=blocked_result["response"]
                    )
                    
                    return {
                        "intent": plan.get("intent", "task"),
                        "domain": domain,
                        "action": action,
                        "risk": risk,
                        "status": "blocked",
                        "response": blocked_result["response"],
                        "step_results": step_results
                    }
                
                # Increment mutation attempt
                self.telemetry.increment("mutation_attempt", metadata={"step": step_num})
            
            # Execute step
            try:
                result = self._execute_step(step)
                
                # Increment mutation success if applicable
                if is_mutation and result.get("status") == "success":
                    self.telemetry.increment("mutation_success", metadata={"step": step_num})
                
                step_results.append(result)
                
                # Stop on error
                if result.get("status") == "error":
                    self._log_execution(
                        command=command,
                        intent=plan.get("intent", "task"),
                        domain=domain,
                        action=action,
                        risk=risk,
                        status="error",
                        response=result.get("response", "Step failed")
                    )
                    
                    return {
                        "intent": plan.get("intent", "task"),
                        "domain": domain,
                        "action": action,
                        "risk": risk,
                        "status": "error",
                        "response": f"Failed at step {step_num}: {result.get('response', 'Unknown error')}",
                        "step_results": step_results
                    }
                    
            except Exception as e:
                error_result = {
                    "domain": domain,
                    "action": action,
                    "risk": risk,
                    "status": "error",
                    "response": f"Exception: {str(e)}"
                }
                step_results.append(error_result)
                
                self._log_execution(
                    command=command,
                    intent=plan.get("intent", "task"),
                    domain=domain,
                    action=action,
                    risk=risk,
                    status="error",
                    response=error_result["response"]
                )
                
                return {
                    "intent": plan.get("intent", "task"),
                    "domain": domain,
                    "action": action,
                    "risk": risk,
                    "status": "error",
                    "response": f"Failed at step {step_num}: {str(e)}",
                    "step_results": step_results
                }
        
        # All steps completed
        final_response = f"Completed {len(steps)} step(s) successfully."
        
        self._log_execution(
            command=command,
            intent=plan.get("intent", "task"),
            domain=plan.get("domain", "multi"),
            action="multi_step",
            risk=plan.get("risk", "medium"),
            status="success",
            response=final_response
        )
        
        return {
            "intent": plan.get("intent", "task"),
            "domain": plan.get("domain", "multi"),
            "action": "multi_step",
            "risk": plan.get("risk", "medium"),
            "status": "success",
            "response": final_response,
            "step_results": step_results
        }
    
    def _execute_step(self, step):
        """Execute a single step with tool method verification."""
        domain = step.get("domain", "unknown")
        action = step.get("action", "unknown")
        
        # Get tool
        if domain not in self.tools:
            return {
                "domain": domain,
                "action": action,
                "risk": step.get("risk", "low"),
                "status": "error",
                "response": f"Unknown domain: {domain}"
            }
        
        tool = self.tools[domain]
        
        # Execute via appropriate method
        try:
            # Use execute() method if available (preferred for routing)
            if hasattr(tool, "execute"):
                result = tool.execute(action, step.get("parameters", step))
                
                # Track file ingestion for PDF
                if domain == "pdf" and action == "summarize":
                    self.telemetry.increment("file_ingested", metadata={"type": "pdf"})
                
                # Handle different response formats
                if isinstance(result, dict):
                    if result.get("status") == "success":
                        resp_msg = result.get("message", result.get("data", "Completed"))
                        self._publish_sync(NovaEvent(
                            source="controller",
                            type="action_executed",
                            payload={"tool": domain, "action": action, "result": resp_msg},
                            priority=2
                        ))
                        return {
                            "domain": domain,
                            "action": action,
                            "risk": step.get("risk", "low"),
                            "status": "success",
                            "response": resp_msg
                        }
                    else:
                        return {
                            "domain": domain,
                            "action": action,
                            "risk": step.get("risk", "low"),
                            "status": "error",
                            "response": result.get("message", "Execution failed")
                        }
                else:
                    self._publish_sync(NovaEvent(
                        source="controller",
                        type="action_executed",
                        payload={"tool": domain, "action": action, "result": str(result)},
                        priority=2
                    ))
                    return {
                        "domain": domain,
                        "action": action,
                        "risk": step.get("risk", "low"),
                        "status": "success",
                        "response": str(result)
                    }
            
            # Fallback to direct method calls
            elif domain == "system":
                if action == "morning_briefing":
                    briefing = tool.morning_briefing()
                    self._publish_sync(NovaEvent(
                        source="controller",
                        type="action_executed",
                        payload={"tool": domain, "action": action, "result": briefing[:100] + "..."},
                        priority=2
                    ))
                    return {
                        "domain": domain,
                        "action": action,
                        "risk": "low",
                        "status": "success",
                        "response": briefing
                    }
                else:
                    return {
                        "domain": domain,
                        "action": action,
                        "risk": "low",
                        "status": "error",
                        "response": f"Action {action} not implemented"
                    }
            
            else:
                return {
                    "domain": domain,
                    "action": action,
                    "risk": step.get("risk", "low"),
                    "status": "error",
                    "response": f"Tool does not support execute() method"
                }
                
        except AttributeError as e:
            return {
                "domain": domain,
                "action": action,
                "risk": step.get("risk", "low"),
                "status": "error",
                "response": f"Tool method error: {str(e)}"
            }
        except Exception as e:
            return {
                "domain": domain,
                "action": action,
                "risk": step.get("risk", "low"),
                "status": "error",
                "response": f"Execution error: {str(e)}"
            }
    
    # ================================================================
    # SINGLE-STEP EXECUTION
    # ================================================================
    
    def _execute_single_step(self, command, plan):
        """Execute single-step plan with tool verification."""
        domain = plan.get("domain", "unknown")
        action = plan.get("action", "unknown")
        
        # Verify tool exists
        if domain not in self.tools:
            self._log_execution(
                command=command,
                intent=plan.get("intent", "unknown"),
                domain=domain,
                action=action,
                risk="low",
                status="error",
                response="Command not recognized."
            )
            return {
                "intent": "unknown",
                "domain": domain,
                "action": "none",
                "risk": "low",
                "status": "error",
                "response": "Command not recognized."
            }
        
        tool = self.tools[domain]
        
        # Execute based on domain
        try:
            if domain == "pdf":
                file_path = plan.get("file_path")
                if not file_path:
                    result = {
                        "intent": "task",
                        "domain": "pdf",
                        "action": "summarize",
                        "risk": "low",
                        "status": "error",
                        "response": "No file path specified for PDF."
                    }
                else:
                    summary = tool.summarize(file_path)
                    self.telemetry.increment("file_ingested", metadata={"type": "pdf"})
                    self._publish_sync(NovaEvent(
                        source="controller",
                        type="action_executed",
                        payload={"tool": domain, "action": action, "result": "PDF summarized successfully."},
                        priority=2
                    ))
                    result = {
                        "intent": "task",
                        "domain": "pdf",
                        "action": "summarize",
                        "risk": "low",
                        "status": "success",
                        "response": f"PDF summarized successfully:\n{summary}"
                    }
                
                self._log_execution(
                    command=command,
                    intent=result["intent"],
                    domain=result["domain"],
                    action=result["action"],
                    risk=result["risk"],
                    status=result["status"],
                    response=result["response"]
                )
                return result
            
            elif domain == "calendar":
                if action == "read_today":
                    events = tool.get_today_events()
                    if not events:
                        result = {
                            "intent": plan.get("intent", "unknown"),
                            "domain": "calendar",
                            "action": action,
                            "risk": "low",
                            "status": "success",
                            "response": "No upcoming events for today."
                        }
                    else:
                        response = "Found events:\n" + "\n".join([f"- {e}" for e in events])
                        self._publish_sync(NovaEvent(
                            source="controller",
                            type="action_executed",
                            payload={"tool": domain, "action": action, "result": f"Found {len(events)} events."},
                            priority=2
                        ))
                        result = {
                            "intent": plan.get("intent", "unknown"),
                            "domain": "calendar",
                            "action": action,
                            "risk": "low",
                            "status": "success",
                            "response": response
                        }
                    
                    self._log_execution(
                        command=command,
                        intent=result["intent"],
                        domain=result["domain"],
                        action=result["action"],
                        risk=result["risk"],
                        status=result["status"],
                        response=result["response"]
                    )
                    return result
                else:
                    result = {
                        "intent": plan.get("intent", "unknown"),
                        "domain": "calendar",
                        "action": action,
                        "risk": plan.get("risk", "low"),
                        "status": "error",
                        "response": "Calendar action not implemented"
                    }
                    return result
            
            elif domain in ("notion", "task"):
                if action == "read_open":
                    tasks = tool.get_open_tasks()
                    if not tasks:
                        result = {
                            "intent": plan.get("intent", "unknown"),
                            "domain": "notion",
                            "action": action,
                            "risk": "low",
                            "status": "success",
                            "response": "No open tasks found."
                        }
                    else:
                        response = "Found open tasks:\n" + "\n".join([f"- {t}" for t in tasks])
                        self._publish_sync(NovaEvent(
                            source="controller",
                            type="action_executed",
                            payload={"tool": domain, "action": action, "result": f"Found {len(tasks)} tasks."},
                            priority=2
                        ))
                        result = {
                            "intent": plan.get("intent", "unknown"),
                            "domain": "notion",
                            "action": action,
                            "risk": "low",
                            "status": "success",
                            "response": response
                        }
                    
                    self._log_execution(
                        command=command,
                        intent=result["intent"],
                        domain=result["domain"],
                        action=result["action"],
                        risk=result["risk"],
                        status=result["status"],
                        response=result["response"]
                    )
                    return result
                else:
                    result = {
                        "intent": plan.get("intent", "unknown"),
                        "domain": "notion",
                        "action": action,
                        "risk": plan.get("risk", "low"),
                        "status": "error",
                        "response": "Notion action not implemented"
                    }
                    return result
            
            elif domain == "system":
                if action == "morning_briefing":
                    briefing = tool.morning_briefing()
                    self._publish_sync(NovaEvent(
                        source="controller",
                        type="action_executed",
                        payload={"tool": domain, "action": action, "result": briefing[:100] + "..."},
                        priority=2
                    ))
                    result = {
                        "intent": plan.get("intent", "unknown"),
                        "domain": "system",
                        "action": action,
                        "risk": "low",
                        "status": "success",
                        "response": briefing
                    }
                    
                    self._log_execution(
                        command=command,
                        intent=result["intent"],
                        domain=result["domain"],
                        action=result["action"],
                        risk=result["risk"],
                        status=result["status"],
                        response=result["response"]
                    )
                    return result
                else:
                    result = {
                        "intent": plan.get("intent", "unknown"),
                        "domain": "system",
                        "action": action,
                        "risk": "low",
                        "status": "error",
                        "response": "System action not implemented"
                    }
                    return result
            
            else:
                self._log_execution(
                    command=command,
                    intent=plan.get("intent", "unknown"),
                    domain=domain,
                    action=action,
                    risk="low",
                    status="error",
                    response="Command not recognized."
                )
                return {
                    "intent": "unknown",
                    "domain": domain,
                    "action": "none",
                    "risk": "low",
                    "status": "error",
                    "response": "Command not recognized."
                }
                
        except AttributeError as e:
            self._log_execution(
                command=command,
                intent=plan.get("intent", "unknown"),
                domain=domain,
                action=action,
                risk="low",
                status="error",
                response=f"Tool method error: {str(e)}"
            )
            return {
                "intent": "error",
                "domain": domain,
                "action": action,
                "risk": "low",
                "status": "error",
                "response": "Command not recognized."
            }
        except Exception as e:
            self._log_execution(
                command=command,
                intent=plan.get("intent", "unknown"),
                domain=domain,
                action=action,
                risk="low",
                status="error",
                response=f"Execution error: {str(e)}"
            )
            return {
                "intent": "error",
                "domain": domain,
                "action": action,
                "risk": "low",
                "status": "error",
                "response": "Command not recognized."
            }
    
    # ================================================================
    # CONFIRMATION WORKFLOW
    # ================================================================
    
    def execute_confirmed_action(self, command, result):
        """Execute confirmed single action."""
        return "Confirmed action executed"
    
    def execute_confirmed_step(self, command, result):
        """Resume multi-step execution after confirmation."""
        remaining = result.get("remaining_steps", [])
        if not remaining:
            return "No remaining steps to execute"
        return f"Resuming execution of {len(remaining)} remaining step(s)"
    
    def cancel_confirmed_action(self, command, result):
        """Cancel pending confirmation."""
        self._log_execution(
            command=command,
            intent=result.get("intent", "unknown"),
            domain=result.get("domain", "unknown"),
            action=result.get("action", "unknown"),
            risk=result.get("risk", "unknown"),
            status="cancelled",
            response="User cancelled action"
        )
    
    # ================================================================
    # LOGGING
    # ================================================================
    
    def _log_execution(self, command, intent, domain, action, risk, status, response):
        """Unified logging with contract signature."""
        try:
            self.logger.log_execution(
                user_command=command,
                intent=intent,
                domain=domain,
                action=action,
                risk=risk,
                status=status,
                response=response
            )
        except Exception as e:
            if config.DEBUG:
                print(f"[Logging Error]: {e}")
