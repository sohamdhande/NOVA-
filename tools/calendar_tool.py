import os
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# OAuth scope — full calendar access and Gmail access
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify"
]

# Credential file paths (project root)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")


class CalendarTool:
    """Reads and creates Google Calendar events via OAuth2."""

    def __init__(self):
        self.service = self._authenticate()

    def _authenticate(self):
        """Load saved token or trigger OAuth flow. Returns Calendar service."""
        creds = None

        # Load existing token
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        # Refresh or start new OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDENTIALS_FILE):
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save token for future runs
            with open(TOKEN_FILE, "w") as token_file:
                token_file.write(creds.to_json())

        return build("calendar", "v3", credentials=creds)

    def get_upcoming_events(self, max_results=5):
        """Fetch the next N events from primary calendar."""
        if not self.service:
            return {
                "status": "error",
                "message": "Google Calendar not authenticated. Place credentials.json in project root.",
                "data": None
            }

        try:
            now = datetime.utcnow().isoformat() + "Z"
            result = self.service.events().list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime"
            ).execute()

            events = result.get("items", [])

            if not events:
                return {
                    "status": "success",
                    "message": "No upcoming events found.",
                    "data": []
                }

            event_list = []
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                event_list.append({
                    "title": event.get("summary", "No title"),
                    "start": start,
                    "id": event["id"]
                })

            return {
                "status": "success",
                "message": f"Found {len(event_list)} upcoming event(s).",
                "data": event_list
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to fetch events: {str(e)}",
                "data": None
            }

    def get_today_events(self):
        """Fetch events for today only."""
        if not self.service:
            return {
                "status": "error",
                "message": "Google Calendar not authenticated. Place credentials.json in project root.",
                "data": None
            }

        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0).isoformat() + "Z"
            today_end = (datetime.utcnow().replace(hour=0, minute=0, second=0) + timedelta(days=1)).isoformat() + "Z"

            result = self.service.events().list(
                calendarId="primary",
                timeMin=today_start,
                timeMax=today_end,
                singleEvents=True,
                orderBy="startTime"
            ).execute()

            events = result.get("items", [])

            if not events:
                return {
                    "status": "success",
                    "message": "No events scheduled for today.",
                    "data": []
                }

            event_list = []
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                event_list.append({
                    "title": event.get("summary", "No title"),
                    "start": start,
                    "id": event["id"]
                })

            return {
                "status": "success",
                "message": f"Found {len(event_list)} event(s) for today.",
                "data": event_list
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to fetch today's events: {str(e)}",
                "data": None
            }

    def create_event(self, title, start_datetime, end_datetime):
        """Create a new calendar event."""
        if not self.service:
            return {
                "status": "error",
                "message": "Google Calendar not authenticated. Place credentials.json in project root.",
                "data": None
            }

        if not title or not start_datetime or not end_datetime:
            return {
                "status": "error",
                "message": "Missing required fields: title, start_datetime, end_datetime.",
                "data": None
            }

        try:
            event_body = {
                "summary": title,
                "start": {"dateTime": start_datetime, "timeZone": "Asia/Kolkata"},
                "end": {"dateTime": end_datetime, "timeZone": "Asia/Kolkata"},
            }

            created = self.service.events().insert(
                calendarId="primary", body=event_body
            ).execute()

            return {
                "status": "success",
                "message": f"Event '{title}' created successfully.",
                "data": {
                    "id": created.get("id"),
                    "link": created.get("htmlLink")
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to create event: {str(e)}",
                "data": None
            }

    def execute(self, action, parameters=None):
        """Route to correct method based on action type."""
        parameters = parameters or {}

        if action == "read":
            max_results = parameters.get("max_results", 5)
            return self.get_upcoming_events(max_results)

        elif action == "read_today":
            return self.get_today_events()

        elif action == "create" or action == "create_event":
            # Map parameters: planner uses "title", tool uses "event_title"
            title = parameters.get("event_title") or parameters.get("title")
            return self.create_event(
                title=title,
                start_datetime=parameters.get("start_datetime"),
                end_datetime=parameters.get("end_datetime")
            )

        else:
            return {
                "status": "error",
                "message": f"Unknown calendar action: {action}",
                "data": None
            }
