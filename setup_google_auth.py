"""
One-time Google Calendar OAuth setup.

Run this locally (NOT in Docker) once to generate token.json.
A browser window will open asking you to sign into the Google account
whose Calendar the AI receptionist should use.

Prerequisite: place credentials.json (downloaded from Google Cloud Console
-> APIs & Services -> Credentials -> OAuth Client ID -> Desktop app)
in this same folder before running this script.

Usage:
    python setup_google_auth.py
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar']


def main():
    if not os.path.exists('credentials.json'):
        print("❌ credentials.json not found.")
        print("   Download it from Google Cloud Console > APIs & Services")
        print("   > Credentials > OAuth Client ID (type: Desktop app)")
        print("   and place it in this folder before running this script.")
        return

    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)

    with open('token.json', 'w') as f:
        f.write(creds.to_json())

    print("✅ token.json created successfully.")
    print("   You can now run: python agent.py console")
    print("   Or copy token.json into your Docker setup before running docker compose up.")


if __name__ == "__main__":
    main()
