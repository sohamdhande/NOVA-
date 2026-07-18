
from storage.memory_store import MemoryStore

class MemoryTool:
    """
    Memory tool with dependency injection.
    
    Accepts MemoryStore instance instead of creating its own.
    """
    
    def __init__(self, memory_store):
        """
        Initialize MemoryTool with injected MemoryStore.
        
        Args:
            memory_store: MemoryStore instance
        """
        self.store = memory_store

    def execute(self, action, parameters):
        if action == "store_entry":
            return self.store_entry(parameters)
        elif action == "search_entries":
            return self.search_entries(parameters)
        elif action == "recall_topic":
            return self.recall_topic(parameters)
        else:
            return {
                "status": "error",
                "message": f"Unknown memory action: {action}"
            }

    def store_entry(self, params):
        """Store a memory entry.
        
        ONLY called when explicit memory intent detected.
        Never as fallback or default action.
        
        Args:
            params: Dictionary with 'data' containing entry details.
            
        Returns:
            dict: Status and message.
        """
        data = params.get("data", {})
        entry = self.store.add_entry(
            project=data.get("project", "general"),
            source_type=data.get("source_type", "manual"),
            title=data.get("title", "Untitled"),
            summary=data.get("summary", ""),
            tags=data.get("tags", [])
        )
        
        # Check if entry was rejected as duplicate
        if isinstance(entry, dict) and entry.get("status") == "duplicate":
            # Duplicate handled silently by store layer
            return {
                "status": "info",
                "message": f"Memory '{entry.get('title')}' already exists (duplicate skipped).",
                "data": entry
            }
        
        # --- TELEMETRY (whitelisted metric) ---
        try:
             from core.telemetry import TelemetryLogger
             TelemetryLogger().increment("memory_stored", metadata={"id": entry["id"]})
        except: 
            pass
        # -----------------
        
        return {
            "status": "success",
            "message": f"Memory stored: '{entry['title']}'",
            "data": entry
        }

    def search_entries(self, params):
        # Support both flat params and nested "data" usage
        query = params.get("query") or params.get("data", {}).get("query", "")
        results = self.store.search(query)
        
        if not results:
             return {"status": "success", "message": "No matching memories found.", "data": []}
        
        # Format results for display
        formatted = "\n".join([f"- [{r['timestamp'][:10]}] {r['title']}: {r['summary']}" for r in results[:5]])
        return {
            "status": "success",
            "message": f"Found {len(results)} entries:\n{formatted}",
            "data": results
        }

    def recall_topic(self, params):
        # Support both flat params and nested "data" usage
        # LLM might use "topic" or "query" inside data
        data = params.get("data", {})
        topic = params.get("topic") or data.get("topic") or data.get("query", "")
        
        results = self.store.recall_topic(topic)
        if not results:
             return {"status": "success", "message": f"No knowledge found on topic '{topic}'.", "data": []}

        formatted = "\n".join([f"- {r['summary']}" for r in results[:5]])
        return {
            "status": "success",
            "message": f"Knowledge on '{topic}':\n{formatted}",
            "data": results
        }
