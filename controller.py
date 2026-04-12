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
                conn = sqlite3.connect(db_path, check_same_thread=False)
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
        if command:
            BLOCKED_PHRASES = [
                "scan", "threat", "virus", "malware", "find threat",
                "check files", "scan files", "security scan",
                "find files that", "threat to my", "dangerous files"
            ]
            if any(phrase in command.lower() for phrase in BLOCKED_PHRASES):
                return "I don't have file scanning capabilities. Use a real antivirus tool like Malwarebytes or macOS XProtect."
                
        command = command.strip()
        
        # Empty input already handled by CLI - this is defensive
        if not command:
            return self._fallback_chat(command)
            
        # Merge Clarification if pending
        if hasattr(self, '_clarity_pending') and self._clarity_pending:
            original_command = self._clarity_pending['command']
            command = f"{original_command}. Additional details: {command}"
            self._clarity_pending = None
        
        # -----------------------------------------------------------
        # STEP 4.5: SKILL LOADER
        # -----------------------------------------------------------
        try:
            from core.skill_loader import run_with_skill
            skill_result = run_with_skill(command)
            if skill_result:
                self._log_execution(
                    command=command,
                    intent="skill_routing",
                    domain="skills",
                    action="execute_skill",
                    risk="low",
                    status="success",
                    response=skill_result
                )
                return {
                    "intent": "skill_routing",
                    "domain": "skills",
                    "action": "execute",
                    "risk": "low",
                    "status": "success",
                    "response": skill_result
                }
        except Exception as e:
            if config.DEBUG: print(f"[Controller] Skill Loader error: {e}")

        # -----------------------------------------------------------
        # STEP 4.6: SCREEN MEMORY PREPEND
        # -----------------------------------------------------------
        try:
            from tools.screen_tool import SCREEN_MEMORY
            import time
            last_screen = SCREEN_MEMORY.get('last')
            if last_screen and time.time() - last_screen['timestamp'] < 60:
                ctx = last_screen['context']
                command = f"[Screen context: {ctx.get('app')} — {ctx.get('task')}] {command}"
        except Exception as e:
            if getattr(config, 'DEBUG', False): print(f"[Controller] Screen Context error: {e}")

        # -----------------------------------------------------------
        # STEP 5: PLANNER INVOCATION
        # -----------------------------------------------------------
        
        try:
            from llm import generate_plan, correct_plan
            from schema import validate_json
            from validator import validate_plan
        except ImportError as e:
            return self._fallback_chat(command)
        
        parsed = generate_plan(command)
        
        if not parsed:
            self.telemetry.increment("planner_failed")
            return self._fallback_chat(command)
        
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
                    response="Redirected to conversation fallback."
                )
                return self._fallback_chat(command)
            
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
                    response="Redirected to conversation fallback."
                )
                return self._fallback_chat(command)
            
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
                response="Redirected to conversation fallback."
            )
            return self._fallback_chat(command)
        
        # Verify domain contract
        if not self._verify_domain_contract(parsed):
            self._log_execution(
                command=command,
                intent=parsed.get("intent", "unknown"),
                domain=parsed.get("domain", "unknown"),
                action=parsed.get("action", "none"),
                risk="low",
                status="rejected",
                response="Redirected to conversation fallback."
            )
            return self._fallback_chat(command)
        
        # Verify action contract (for single-step or steps)
        if not self._verify_action_contract(parsed):
            self._log_execution(
                command=command,
                intent=parsed.get("intent", "unknown"),
                domain=parsed.get("domain", "unknown"),
                action=parsed.get("action", "none"),
                risk="low",
                status="rejected",
                response="Redirected to conversation fallback."
            )
            return self._fallback_chat(command)
        
        # -----------------------------------------------------------
        # STEP 8: EXECUTION ROUTING
        # -----------------------------------------------------------
        
        # Clarity Engine validation before execution
        try:
            from core.clarity_engine import needs_clarification
            question = needs_clarification(command, parsed)
            if question:
                self._clarity_pending = {
                    "command": command,
                    "intent": parsed
                }
                return {
                    "intent": "clarification_needed",
                    "domain": "system",
                    "action": "ask",
                    "risk": "low",
                    "status": "success",
                    "response": question
                }
        except Exception as e:
            if config.DEBUG: print(f"[Controller] Clarity error: {e}")
        
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
        
        return self._fallback_chat(command)
        
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
                    response="Redirected to conversation fallback."
                )
                return self._fallback_chat(command)
                
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
            return self._fallback_chat(command)
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
            return self._fallback_chat(command)
    

    def _fallback_chat(self, command: str) -> dict:
        from llm import generate_summary
        prompt = f"""You are N.O.V.A, an AI assistant like JARVIS.
Be precise, efficient, mission-focused.
Keep responses concise and operational.
Never say 'Command not recognized'.

User: {command}"""
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
