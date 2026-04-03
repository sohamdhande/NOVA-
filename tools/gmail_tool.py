import os
import base64
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify"
]

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")


class GmailTool:
    """Reads, summarizes, and sends Gmail emails using OAuth2."""

    def __init__(self):
        self.service = self._authenticate()

    def _authenticate(self):
        """Load saved token or trigger OAuth flow. Returns Gmail service."""
        creds = None

        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

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

            with open(TOKEN_FILE, "w") as token_file:
                token_file.write(creds.to_json())

        return build("gmail", "v1", credentials=creds)

    def read_emails(self, max_results=10, sender=None):
        """Fetch latest unread emails from INBOX."""
        if not self.service:
            return {"status": "error", "message": "Google not authenticated."}

        query = "is:unread in:inbox"
        if sender:
            query += f" from:{sender}"

        try:
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []

            for msg in messages:
                full_msg = self.service.users().messages().get(
                    userId='me', id=msg['id'], format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = full_msg.get('payload', {}).get('headers', [])
                headers_dict = {h['name']: h['value'] for h in headers}

                emails.append({
                    "id": msg['id'],
                    "from": headers_dict.get('From', ''),
                    "subject": headers_dict.get('Subject', ''),
                    "date": headers_dict.get('Date', ''),
                    "snippet": full_msg.get('snippet', '')
                })

            return {"status": "success", "data": emails}
        except Exception as e:
            return {"status": "error", "message": f"Failed to read emails: {str(e)}"}

    def get_email_body(self, email_id: str):
        """Fetch full email body by ID and decode base64 content."""
        if not self.service:
            return "Not authenticated."

        try:
            msg = self.service.users().messages().get(
                userId='me', id=email_id, format='full'
            ).execute()
            payload = msg.get('payload', {})

            def extract_text(parts):
                text = ""
                for part in parts:
                    if part.get('mimeType') == 'text/plain':
                        data = part.get('body', {}).get('data', '')
                        if data:
                            text += base64.urlsafe_b64decode(data).decode('utf-8')
                    elif 'parts' in part:
                        text += extract_text(part['parts'])
                return text

            if 'parts' in payload:
                body = extract_text(payload['parts'])
            else:
                data = payload.get('body', {}).get('data', '')
                body = base64.urlsafe_b64decode(data).decode('utf-8') if data else ""

            return body
        except Exception as e:
            return f"Error fetching body: {str(e)}"

    def send_email(self, to: str, subject: str, body: str):
        """Send email via Gmail API."""
        if not self.service:
            return {"status": "failed", "error": "Not authenticated."}

        try:
            message = EmailMessage()
            message.set_content(body)
            message['To'] = to
            message['Subject'] = subject

            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {'raw': encoded_message}

            sent = self.service.users().messages().send(userId="me", body=create_message).execute()
            return {"status": "sent", "id": sent['id']}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def summarize_inbox(self, max_results=10):
        """Call read_emails(), pass to llm, return summary string."""
        result = self.read_emails(max_results)
        if result.get('status') != 'success':
            return result.get('message', 'Error reading inbox')

        emails = result.get('data', [])
        if not emails:
            return "No unread emails in inbox."

        raw_inbox = "\n\n".join([
            f"From: {e['from']}\nSubject: {e['subject']}\nSnippet: {e['snippet']}"
            for e in emails
        ])

        try:
            import sys
            sys.path.append(BASE_DIR)
            from llm import _chat
            summary = _chat(
                system=(
                    "You are NOVA, a highly advanced executive assistant. Summarize these emails into a clean, structured inbox briefing.\n"
                    "Format strictly using Markdown with the following structure:\n\n"
                    "## 📥 Inbox Briefing\n\n"
                    "### 🚨 Action Required\n"
                    "(List highly urgent/important items here, or 'None' if empty)\n"
                    "- **[Sender Name]** | *[Subject]*\n"
                    "  ↳ [1-line crisp summary]\n\n"
                    "### ℹ️ General Updates\n"
                    "- **[Sender Name]** | *[Subject]*\n"
                    "  ↳ [1-line crisp summary]\n\n"
                    "Ensure perfectly clean spacing, no filler text, and a crisp executive tone."
                ),
                user=f"Emails:\n{raw_inbox}"
            )
            return summary
        except Exception as e:
            return f"Failed to summarize inbox: {str(e)}"
