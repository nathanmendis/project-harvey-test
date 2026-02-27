import os
import django
import json
from dotenv import load_dotenv

# Load .env first
load_dotenv()

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')
django.setup()

from core.models.recruitment import Organization
from core.utils.encryption import decrypt_token
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def check_org_calendar():
    # Specifically target "Project Harvey"
    org = Organization.objects.filter(name__icontains="Project Harvey").first()
    if not org:
        org = Organization.objects.exclude(google_refresh_token__isnull=True).exclude(google_refresh_token='').first()
    
    if not org:
        print("No organization found with a Google token in DB.")
        return

    print(f"--- Diagnostic for Organization: {org.name} ---")
    
    try:
        refresh_token = decrypt_token(org.google_refresh_token)
    except Exception as e:
        print(f"Token decryption failed: {e}")
        return

    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("ERROR: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not found in environment.")
        return

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/calendar"]
    )

    try:
        creds.refresh(Request())
        print("Token refresh: SUCCESS")
    except Exception as e:
        print(f"Token refresh failed: {e}")
        return

    service = build('calendar', 'v3', credentials=creds)
    
    try:
        # 1. User Timezone Setting
        setting = service.settings().get(setting='timezone').execute()
        print(f"User Setting Timezone: {setting.get('value')}")
        
        # 2. Primary Calendar Metadata
        calendar = service.calendars().get(calendarId='primary').execute()
        print(f"Primary Calendar TimeZone: {calendar.get('timeZone')}")

        # 3. List all calendars to check individual overrides
        print("\n--- Calendar List Details ---")
        calendar_list = service.calendarList().list().execute()
        for item in calendar_list.get('items', []):
            print(f"- {item.get('summary')} (ID: {item.get('id')})")
            print(f"  Timezone: {item.get('timeZone')}")
            if item.get('primary'):
                print("  [THIS IS THE PRIMARY CALENDAR]")
        
    except Exception as e:
        print(f"Google API error: {e}")

if __name__ == "__main__":
    check_org_calendar()
