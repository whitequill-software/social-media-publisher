"""
One-time script to get a Google Drive OAuth refresh token.

Setup:
1. pip install google-auth-oauthlib google-auth --break-system-packages
2. Put your downloaded client_secret_....json in the same folder as this script,
   and rename it to client_secret.json (or update CLIENT_SECRET_FILE below).
3. Run: python get_refresh_token.py
4. A browser window will open — log in and approve access.
5. The refresh token will print in your terminal. Copy it into your .env file
   as GDRIVE_REFRESH_TOKEN=... (also save the client ID and client secret from
   the same JSON file into .env as GDRIVE_CLIENT_ID and GDRIVE_CLIENT_SECRET).
"""

from google_auth_oauthlib.flow import InstalledAppFlow

# This must match the unattended runtime scope. It permits reading existing
# images in the configured folder but does not permit modifying Drive files.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

CLIENT_SECRET_FILE = "client_secret.json"


def main():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    creds = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
    )

    print("\n=== SAVE THESE INTO YOUR .env FILE ===")
    print(f"GDRIVE_CLIENT_ID={creds.client_id}")
    print(f"GDRIVE_CLIENT_SECRET={creds.client_secret}")
    print(f"GDRIVE_REFRESH_TOKEN={creds.refresh_token}")
    print("=======================================\n")


if __name__ == "__main__":
    main()
