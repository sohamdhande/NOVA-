import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from notion_client import Client, APIResponseError

# Configure logging
logger = logging.getLogger(__name__)

# Load local .env if present
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    try:
        with open(_env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())
    except Exception as e:
        logger.warning(f"Failed to load .env file: {e}")

# Read from environment
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

class NotionTool:
    """Read, create, and update tasks in Notion using official SDK."""

    def __init__(self):
        self.client = None
        if NOTION_API_KEY:
            try:
                self.client = Client(auth=NOTION_API_KEY)
            except Exception as e:
                logger.error(f"Failed to initialize Notion Client: {e}")
        else:
            logger.warning("NOTION_API_KEY not set found in environment")

    def _validate_config(self) -> Optional[Dict[str, Any]]:
        """Check if API key and Database ID are configured."""
        if not self.client:
            return {
                "status": "error",
                "message": "Notion API key not configured. Set NOTION_API_KEY environment variable.",
                "data": None
            }
        if not NOTION_DATABASE_ID:
            return {
                "status": "error",
                "message": "Notion database ID not configured. Set NOTION_DATABASE_ID environment variable.",
                "data": None
            }
        return None

    def _format_error_response(self, error_message: str) -> Dict[str, Any]:
        """Return a standardized error response."""
        return {
            "status": "error",
            "message": error_message,
            "data": None
        }

    def _handle_api_error(self, e: APIResponseError) -> Dict[str, Any]:
        """Safely handle APIResponseError which may change between versions."""
        # v2.x APIResponseError uses .code and .message in older versions, 
        # but modern ones might not expose .message directly or it might be missing.
        # Safest is to use str(e) which includes the message.
        msg = str(e)
        code = getattr(e, "code", "Unknown")
        return self._format_error_response(f"Notion API Error ({code}): {msg}")

    def _tasks_from_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract simplified task data from Notion API response."""
        tasks = []
        for page in results:
            try:
                props = page.get("properties", {})
                
                # Extract Title
                title = "Untitled"
                title_prop = props.get("Name") or props.get("Title") or props.get("Task")
                
                if title_prop and title_prop.get("title"):
                    title_list = title_prop.get("title", [])
                    if title_list:
                         title = title_list[0].get("plain_text", "Untitled")

                # Extract Status
                status = "No status"
                status_prop = props.get("Status")
                if status_prop:
                    prop_type = status_prop.get("type")
                    if prop_type == "status":
                        status = status_prop.get("status", {}).get("name", "No status")
                    elif prop_type == "select":
                        select_obj = status_prop.get("select")
                        if select_obj:
                            status = select_obj.get("name", "No status")

                tasks.append({
                    "id": page["id"],
                    "title": title,
                    "status": status,
                    "url": page.get("url")
                })
            except Exception as e:
                logger.warning(f"Skipping malformed task item {page.get('id')}: {e}")
                continue
                
        return tasks

    def read_tasks(self, limit: int = 5) -> Dict[str, Any]:
        """Fetch recent tasks from the database."""
        if error := self._validate_config():
            return error

        try:
            if hasattr(self.client.databases, "query"):
                response = self.client.databases.query(
                    database_id=NOTION_DATABASE_ID,
                    page_size=limit
                )
            else:
                response = self.client.request(
                    path=f"databases/{NOTION_DATABASE_ID}/query",
                    method="POST",
                    body={"page_size": limit}
                )
            
            tasks = self._tasks_from_results(response.get("results", []))
            
            return {
                "status": "success",
                "message": f"Found {len(tasks)} task(s).",
                "data": tasks
            }

        except APIResponseError as e:
            return self._handle_api_error(e)
        except Exception as e:
            return self._format_error_response(f"Failed to fetch tasks: {str(e)}")

    def read_open_tasks(self, limit: int = 10) -> Dict[str, Any]:
        """Fetch tasks where Status is not 'Done'."""
        if error := self._validate_config():
            return error

        try:
            filter_params = {
                "property": "Status",
                "status": {
                    "does_not_equal": "Done"
                }
            }

            if hasattr(self.client.databases, "query"):
                response = self.client.databases.query(
                    database_id=NOTION_DATABASE_ID,
                    page_size=limit,
                    filter=filter_params
                )
            else:
                response = self.client.request(
                    path=f"databases/{NOTION_DATABASE_ID}/query",
                    method="POST",
                    body={
                        "page_size": limit,
                        "filter": filter_params
                    }
                )
            
            tasks = self._tasks_from_results(response.get("results", []))
            
            return {
                "status": "success",
                "message": f"Found {len(tasks)} open task(s).",
                "data": tasks
            }

        except APIResponseError as e:
            return self._handle_api_error(e)
        except Exception as e:
            return self._format_error_response(f"Failed to fetch open tasks: {str(e)}")

    def create_task(self, title: str) -> Dict[str, Any]:
        """Create a new page in the database."""
        if error := self._validate_config():
            return error
            
        if not title:
            return self._format_error_response("Task title is required.")

        try:
            new_page = self.client.pages.create(
                parent={"database_id": NOTION_DATABASE_ID},
                properties={
                    "Name": {
                        "title": [
                            {
                                "text": {
                                    "content": title
                                }
                            }
                        ]
                    },
                    "Status": {
                        "status": {
                            "name": "Not started"
                        }
                    }
                }
            )

            return {
                "status": "success",
                "message": f"Task '{title}' created successfully.",
                "data": {"id": new_page["id"], "url": new_page.get("url")}
            }

        except APIResponseError as e:
            return self._handle_api_error(e)
        except Exception as e:
             return self._format_error_response(f"Failed to create task: {str(e)}")

    def update_task_status(self, task_id: str, status: str) -> Dict[str, Any]:
        """Update the status property of a page."""
        if error := self._validate_config():
            return error

        if not task_id:
             return self._format_error_response("Task ID is required.")

        try:
            self.client.pages.update(
                page_id=task_id,
                properties={
                    "Status": {
                        "status": {
                            "name": status
                        }
                    }
                }
            )

            return {
                "status": "success",
                "message": f"Task status updated to '{status}'.",
                "data": {"id": task_id, "new_status": status}
            }

        except APIResponseError as e:
            return self._handle_api_error(e)
        except Exception as e:
            return self._format_error_response(f"Failed to update task status: {str(e)}")

    def execute(self, action: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Dispatcher for tool actions."""
        parameters = parameters or {}
        
        # Map actions to methods
        if action == "read":
            return self.read_tasks(limit=parameters.get("limit", 5))
            
        elif action == "read_open":
            return self.read_open_tasks(limit=parameters.get("limit", 10))
            
        elif action == "create":
            return self.create_task(title=parameters.get("task_title") or parameters.get("title"))
            
        elif action == "update":
            return self.update_task_status(
                task_id=parameters.get("task_id") or parameters.get("id"),
                status=parameters.get("task_status") or parameters.get("status", "Done")
            )
            
        else:
            return self._format_error_response(f"Unknown action: {action}")
