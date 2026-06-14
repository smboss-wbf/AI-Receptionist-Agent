"""
Google Calendar OAuth Setup
Run this ONCE to generate token.json
After that, calendar.py uses token.json automatically

Steps:
1. Go to console.cloud.google.com
2. Create a project
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download as credentials.json
6. Run: python setup_google_auth.py
"""

import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/calendar']

def setup():
    creds = None

    # Check if token already exists
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If no valid token, run OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("ERROR: credentials.json not found!")
                print("Download it from Google Cloud Console:")
                print("console.cloud.google.com → APIs → OAuth 2.0 Credentials → Download")
                return

            print("Opening browser for Google authentication...")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for future use
        with open('token.json', 'w') as f:
            f.write(creds.to_json())
        print("✅ token.json saved successfully!")
        print("You can now run agent.py and mcp_server.py")

    else:
        print("✅ Token already valid — you're good to go!")

if __name__ == "__main__":
    setup()
