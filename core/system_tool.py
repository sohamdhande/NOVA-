class SystemTool:
    """Stub for system-level actions.

    Orchestration logic lives in controller._handle_system().
    This class exists as an extension point for future system actions
    that don't require cross-tool orchestration.
    """

    def __init__(self):
        pass

    def execute(self, action, parameters=None):
        """Route to system action methods."""
        parameters = parameters or {}

        return {
            "status": "error",
            "message": f"Unknown system action: {action}",
            "data": None
        }
