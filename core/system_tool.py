from llm import generate_summary

class SystemTool:
    """System-level actions that don't satisfy the tool interface but need isolation."""

    def __init__(self):
        pass

    def execute(self, action, parameters=None):
        """Route to system action methods."""
        parameters = parameters or {}

        if action == "morning_briefing":
            return self._morning_briefing(
                events=parameters.get("events"),
                tasks=parameters.get("tasks")
            )

        return {
            "status": "error",
            "message": f"Unknown system action: {action}",
            "data": None
        }

    def _morning_briefing(self, events, tasks):
        """Generate a morning briefing from provided data."""
        # Ensure lists
        events = events or []
        tasks = tasks or []
        
        # Determine context for LLM
        context = {
            "events": events if events else None,
            "tasks": tasks if tasks else None
        }
        
        try:
            briefing = generate_summary(context)
            return {
                "status": "success",
                "message": "Briefing generated.",
                "response": briefing,
                "data": {"briefing": briefing}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to generate briefing: {str(e)}",
                "data": None
            }
