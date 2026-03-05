
import os
import shutil
import time
from llm import analyze_file_action
from tools.pdf_tool import PDFTool
from tools.memory_tool import MemoryTool
from tools.notion_tool import NotionTool
from storage.logger import ExecutionLogger
from core.telemetry import TelemetryLogger

class InboxWatcher:

    def __init__(self, memory_tool, notion_tool, pdf_tool, inbox_dir="inbox", processed_dir="processed", queue_file="queue/pending.json"):
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.inbox_path = os.path.join(self.base_dir, inbox_dir)
        self.processed_path = os.path.join(self.base_dir, processed_dir)
        self.queue_file = os.path.join(self.base_dir, queue_file)
        self.logger = ExecutionLogger()
        
        # Dependency Injection
        self.memory_tool = memory_tool
        self.notion_tool = notion_tool
        self.pdf_tool = pdf_tool
        
        self._ensure_dirs()

    def _ensure_dirs(self):
        os.makedirs(self.inbox_path, exist_ok=True)
        os.makedirs(self.processed_path, exist_ok=True)
        os.makedirs(os.path.dirname(self.queue_file), exist_ok=True)
        if not os.path.exists(self.queue_file):
            import json
            with open(self.queue_file, "w") as f:
                json.dump([], f)

    def scan(self, safe_mode=False):
        """Process all files in inbox.
        
        Args:
            safe_mode (bool): If True, queue high-risk actions instead of executing.
        """
        files = [f for f in os.listdir(self.inbox_path) if not f.startswith('.')]
        if not files:
            return {"status": "empty", "message": "Inbox is empty.", "processed_files": []}
        
        results = []
        processed_files = []
        for filename in files:
            file_path = os.path.join(self.inbox_path, filename)
            if os.path.isdir(file_path):
                continue
                
            results.append(f"Processing: {filename}")
            try:
                self._process_file(filename, file_path, safe_mode)
                
                # Move to processed
                timestamp = int(time.time())
                dest_name = f"{timestamp}_{filename}"
                shutil.move(file_path, os.path.join(self.processed_path, dest_name))
                results.append(f"  -> Moved to processed/{dest_name}")
                
                # --- TELEMETRY ---
                telemetry = TelemetryLogger()
                telemetry.increment("file_ingested", metadata={"filename": filename})
                # -----------------
                
                processed_files.append({"filename": filename, "status": "success"})
            except Exception as e:
                results.append(f"  -> Error: {str(e)}")
                processed_files.append({"filename": filename, "status": "error", "error": str(e)})
        
        return {
            "status": "processed",
            "message": "\n".join(results),
            "processed_files": processed_files
        }

    def _process_file(self, filename, file_path, safe_mode):
        ext = os.path.splitext(filename)[1].lower()
        context = {
            "file_name": filename,
            "file_path": file_path,
            "file_type": ext.replace(".", "").upper()
        }

        # Step 1: Initial Analysis
        action_plan = analyze_file_action(context)
        action = action_plan.get("action", "ignore")

        if action == "ignore":
            print(f"  [Ignored] {filename}")
            return

        summary_text = ""

        # Execute Summarization Step
        if action == "summarize_document":
            print(f"  [Summarizing] {filename}...")
            if ext == ".pdf":
                # Use injected tool
                result = self.pdf_tool.execute(file_path)
                if result["status"] == "success":
                    summary_text = result["summary"]
                else:
                    raise Exception(f"PDF Error: {result['message']}")
            elif ext in (".txt", ".md"):
                with open(file_path, "r") as f:
                    content = f.read()
                    # Mock summary for text files for now (or use LLM)
                    summary_text = content[:500] + "..." 
            
            # Step 2: Post-Summarization Actions
            if summary_text:
                context["extracted_text"] = summary_text
                # Ask agent what to do with the summary
                next_plan = analyze_file_action(context)
                next_action = next_plan.get("action")
                
                if next_action == "create_notion_entry":
                    if safe_mode:
                        import json
                        print(f"  [Queued] Notion Task creation pending confirmation.")
                        with open(self.queue_file, "r") as f:
                            queue = json.load(f)
                        queue.append({
                            "type": "notion",
                            "requires_confirmation": True,
                            "description": f"Create Notion Task from {filename}",
                            "data": next_plan.get("data", {}),
                            "timestamp": int(time.time())
                        })
                        with open(self.queue_file, "w") as f:
                            json.dump(queue, f, indent=2)
                    else:
                        print(f"  [Notion] Creating task...")
                        # Use injected tool
                        data = next_plan.get("data", {})
                        # Map to NotionTool expected params
                        self.notion_tool.create_task(title=data.get("title", filename))
                    
                    # Also store memory? Memory is safe? Yes, mostly read-heavy later.
                    # But per requirements: "Not auto-confirm high-risk mutations."
                    # Memory store is generally low risk, so we proceed with memory store
                    # UNLESS specifically asked to queue all.
                    # Let's assume memory store is safe enough for daemon.
                    
                    print(f"  [Memory] Storing entry...")
                    # Use injected tool
                    self.memory_tool.store_entry({"data": {
                        "source_type": "file",
                        "title": data.get("title", filename),
                        "summary": data.get("content_summary", summary_text),
                        "tags": data.get("tags", [])
                    }})

                elif next_action == "store_memory_entry":
                     print(f"  [Memory] Storing entry...")
                     # Use injected tool
                     self.memory_tool.execute("store_entry", next_plan)

