from integrations.base import CalendarService as BaseCalendarService
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import json
import logging



class CalendarService(BaseCalendarService):
    def __init__(self, user=None):
        super().__init__(user)
        self.creds = None
        self._authenticate()
    def get_service(self):
        from googleapiclient.discovery import build
        return build("calendar", "v3", credentials=self.creds)

    def _authenticate(self):
        """Build credentials from Organization Token (priority) or System Env Tokens."""
        refresh_token = None
        
        # 1. Organization Token (if user context exists)
        if self.user and hasattr(self.user, 'organization') and self.user.organization:
            from core.utils.encryption import decrypt_token
            encrypted_token = self.user.organization.google_refresh_token
            if encrypted_token:
                try:
                    refresh_token = decrypt_token(encrypted_token)
                except Exception as e:
                    print(f"Failed to decrypt org token: {e}")
        
        # 2. System Token (Fallback)
        if not refresh_token:
            refresh_token = os.environ.get("GOOGLE_SYSTEM_REFRESH_TOKEN")

        if not refresh_token:
             raise ValueError("No Email/Calendar Integration found. Please connect Google Workspace in Settings.")

        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

        self.creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/calendar"] 
        )

        try:
            self.creds.refresh(Request())
        except Exception as e:
            raise ValueError(f"Failed to refresh token: {e}")

    def get_auth_url(self):
        pass
    
    def handle_callback(self, code):
         pass
    
    def get_credentials(self):
        return self.creds

    def create_event(self, title, start_time, end_time, attendees=None, description=None,timezone="Asia/Kolkata"):
        """Create a calendar event using Google Calendar API."""
        if not self.creds:
            raise ValueError("Not authenticated")

        
        service = build('calendar', 'v3', credentials=self.creds)

        if isinstance(attendees, str):
            attendee_list = [{'email': email.strip()} for email in attendees.split(',') if email.strip()]
        elif isinstance(attendees, list):
            attendee_list = [{'email': email} for email in attendees]
        else:
            attendee_list = []

        # ABSOLUTE FIX: Send both dateTime WITH offset AND explicit timeZone key.
        # This tells Google: "The time is already in IST, AND display it in IST."
        event = {
            'summary': title,
            'description': description or "",
            'start': {
                'dateTime': start_time,
                "timeZone": timezone,

            },
            'end': {
                'dateTime': end_time,
                "timeZone": timezone,
            },
            'attendees': attendee_list,
        }
        
        

        try:
            event_result = service.events().insert(calendarId='primary', body=event).execute()
            
            return event_result
        except Exception as e:
            raise e
