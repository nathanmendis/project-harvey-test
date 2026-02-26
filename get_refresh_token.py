import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

# Load environment variables from .env
load_dotenv()

# To run this script, you will need to install the google-auth-oauthlib package:
# pip install google-auth-oauthlib python-dotenv

# Set up the scopes required by your application.
# For sending email via Gmail, the scope is typically:
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def main():
    print("Google OAuth2 Refresh Token Generator")
    print("-" * 40)
    
    # Read from .env
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        print("Client ID and Client Secret are required.")
        return

    client_config = {
        "installed": {
            "client_id": client_id,
            "project_id": "google-oauth-generator", # Placeholder
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost:8080/"],
        }
    }

    try:
        # Create the flow using the client configuration
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        
        # Run the local server flow to authenticate the user
        print("\nA browser window will open to prompt you for authorization.")
        print("Please log in with the Google account you want to use for the app.")
        print("NOTE: Make sure http://localhost:8080/ is added to your 'Authorized redirect URIs' in Google Cloud Console.")
        creds = flow.run_local_server(port=8080, prompt="consent")

        print("\n" + "=" * 50)
        print("Authentication Successful!")
        print("=" * 50)
        print(f"\nYour new GOOGLE_SYSTEM_REFRESH_TOKEN is:\n")
        print(creds.refresh_token)
        print("\n" + "=" * 50)
        print("IMPORTANT: Copy the refresh token above and paste it into your .env file.")
        
    except Exception as e:
        print(f"\nAn error occurred during authentication: {e}")

if __name__ == '__main__':
    main()
