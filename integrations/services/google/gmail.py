from integrations.services.base import EmailService
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText
import os

class GmailService(EmailService):
    def __init__(self, user=None):
        # User is optional now, as we use system creds
        super().__init__(user)
        self.creds = None
        self._authenticate()

    def _authenticate(self):
        """Build credentials from System Env Tokens."""
        refresh_token = os.environ.get("GOOGLE_SYSTEM_REFRESH_TOKEN")
        
        if not refresh_token:
            # Fallback to user token if system token not set (backward compatibility)
            if self.user and self.user.google_refresh_token:
                 refresh_token = self.user.google_refresh_token
            else:
                 raise ValueError("No GOOGLE_SYSTEM_REFRESH_TOKEN found in .env (and no user token available).")

        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

        self.creds = Credentials(
            token=None, # We let it refresh immediately
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/gmail.send"]
        )

        # Force refresh to get a valid access token
        try:
            self.creds.refresh(Request())
        except Exception as e:
            raise ValueError(f"Failed to refresh system token: {e}")

    def get_auth_url(self):
        # Handled by core/auth_views.py
        pass
    
    def handle_callback(self, code):
         # Handled by core/auth_views.py
         pass
    
    def get_credentials(self):
        return self.creds

    def send_email(self, recipient_email, subject, body, html_content=None):
        """Send an email using Gmail API."""
        if not self.creds:
            print("❌ GmailService Error: Not authenticated")
            raise ValueError("Not authenticated")

        print(f"📧 Sending email to {recipient_email} via Gmail API...")
        service = build('gmail', 'v1', credentials=self.creds)

        message = MIMEText(html_content if html_content else body, 'html' if html_content else 'plain')
        message['to'] = recipient_email
        message['subject'] = subject
        
        # 'me' is the special value for the authenticated user
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        try:
            message_box = {'raw': raw_message}
            sent_message = service.users().messages().send(userId="me", body=message_box).execute()
            print(f"✅ Email SENT Successfully! Message ID: {sent_message.get('id')}")
            return sent_message
        except Exception as e:
            print(f"❌ Error sending email: {e}")
            raise e
