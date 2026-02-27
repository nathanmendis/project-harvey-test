import os
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load .env file
load_dotenv()

def check_calendar_timezone():
    refresh_token = os.environ.get("GOOGLE_SYSTEM_REFRESH_TOKEN")
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

    if not all([refresh_token, client_id, client_secret]):
        print("ERROR: Missing required environment variables.")
        return

    # Omitting specific scopes to let Google use the scopes originally authorized for this refresh token
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret
    )

    try:
        if creds.expired or not creds.valid:
            creds.refresh(Request())
    except Exception as e:
        print(f"Error refreshing credentials: {e}")
        return

    service = build('calendar', 'v3', credentials=creds)
    
    try:
        # Get primary calendar metadata
        calendar = service.calendars().get(calendarId='primary').execute()
        print(f"\n--- Primary Calendar Metadata ---")
        print(json.dumps(calendar, indent=2))
        print(f"---------------------------------")
        
        # List all calendars
        print("\n--- List of Calendars ---")
        calendar_list = service.calendarList().list().execute()
        for item in calendar_list.get('items', []):
            print(f"- {item.get('summary')} (ID: {item.get('id')}, TimeZone: {item.get('timeZone')})")
        print(f"--------------------------")

    except Exception as e:
        print(f"Error fetching calendar info: {e}")

if __name__ == "__main__":
    check_calendar_timezone()
