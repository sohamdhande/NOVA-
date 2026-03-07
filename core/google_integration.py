import os
import json
import pickle
from datetime import datetime, timedelta

class GoogleIntegration:
    """
    Google Workspace integration.
    Uses OAuth2 — user must authenticate once.
    Credentials stored in ~/.nova/google_token.pkl
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/drive.file'
    ]
    TOKEN_PATH = os.path.expanduser(
        "~/.nova/google_token.pkl"
    )
    CREDS_PATH = os.path.expanduser(
        "~/.nova/google_credentials.json"
    )
    
    def __init__(self):
        self._creds = None
        self._gmail = None
        self._calendar = None
        self._drive = None
    
    def authenticate(self) -> bool:
        """Authenticate with Google OAuth2."""
        try:
            from google.oauth2.credentials import (
                Credentials
            )
            from google_auth_oauthlib.flow import (
                InstalledAppFlow
            )
            from google.auth.transport.requests import (
                Request
            )
            
            if os.path.exists(self.TOKEN_PATH):
                with open(self.TOKEN_PATH, 'rb') as f:
                    self._creds = pickle.load(f)
            
            if not self._creds or \
               not self._creds.valid:
                if self._creds and \
                   self._creds.expired and \
                   self._creds.refresh_token:
                    self._creds.refresh(Request())
                else:
                    if not os.path.exists(
                        self.CREDS_PATH
                    ):
                        return False
                    flow = InstalledAppFlow\
                        .from_client_secrets_file(
                            self.CREDS_PATH,
                            self.SCOPES
                        )
                    self._creds = flow\
                        .run_local_server(port=0)
                
                with open(self.TOKEN_PATH, 'wb') as f:
                    pickle.dump(self._creds, f)
            
            self._build_services()
            return True
        except Exception as e:
            print(f"[Google] Auth failed: {e}")
            return False
    
    def _build_services(self):
        from googleapiclient.discovery import build
        self._gmail = build(
            'gmail', 'v1',
            credentials=self._creds
        )
        self._calendar = build(
            'calendar', 'v3',
            credentials=self._creds
        )
        self._drive = build(
            'drive', 'v3',
            credentials=self._creds
        )
    
    def get_emails(self, 
                    max_results: int = 5) -> list:
        """Get recent unread emails."""
        if not self._gmail:
            return []
        try:
            results = self._gmail.users()\
                .messages().list(
                    userId='me',
                    q='is:unread',
                    maxResults=max_results
                ).execute()
            
            emails = []
            for msg in results.get(
                'messages', []
            ):
                full = self._gmail.users()\
                    .messages().get(
                        userId='me',
                        id=msg['id'],
                        format='metadata',
                        metadataHeaders=[
                            'From', 'Subject', 'Date'
                        ]
                    ).execute()
                
                headers = {
                    h['name']: h['value']
                    for h in full.get(
                        'payload', {}
                    ).get('headers', [])
                }
                emails.append({
                    'id': msg['id'],
                    'from': headers.get(
                        'From', ''
                    ),
                    'subject': headers.get(
                        'Subject', ''
                    ),
                    'date': headers.get('Date', '')
                })
            return emails
        except Exception as e:
            return []
    
    def create_calendar_event(
            self, title: str,
            start: str, end: str,
            description: str = "") -> str:
        """Create Google Calendar event."""
        if not self._calendar:
            return "Google Calendar not connected."
        try:
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start,
                    'timeZone': 'Asia/Kolkata'
                },
                'end': {
                    'dateTime': end,
                    'timeZone': 'Asia/Kolkata'
                }
            }
            result = self._calendar.events()\
                .insert(
                    calendarId='primary',
                    body=event
                ).execute()
            return (f"Calendar event created: "
                    f"{title}")
        except Exception as e:
            return f"Calendar error: {e}"
    
    def upload_to_drive(self, 
                         file_path: str,
                         folder_id: str = None
                         ) -> str:
        """Upload file to Google Drive."""
        if not self._drive:
            return "Google Drive not connected."
        try:
            from googleapiclient.http import (
                MediaFileUpload
            )
            name = os.path.basename(file_path)
            meta = {'name': name}
            if folder_id:
                meta['parents'] = [folder_id]
            media = MediaFileUpload(file_path)
            result = self._drive.files()\
                .create(
                    body=meta,
                    media_body=media,
                    fields='id,name'
                ).execute()
            return (f"Uploaded to Drive: "
                    f"{result['name']}")
        except Exception as e:
            return f"Drive upload error: {e}"

google = GoogleIntegration()
