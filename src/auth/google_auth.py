"""
# src/auth/google_auth.py
# Handles Google OAuth2 authentication and token management
"""

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GoogleAuthManager:
    def __init__(self, credentials_dir: str = "credentials"):
        self.credentials_dir = Path(credentials_dir)
        self.credentials_dir.mkdir(exist_ok=True)
        
    def get_credentials(self, account_id: str) -> Credentials:
        """Get valid credentials for the specified account."""
        creds = None
        token_path = self.credentials_dir / f"{account_id}_token.pickle"
        credentials_path = self.credentials_dir / f"{account_id}_credentials.json"

        # Load existing token if available
        if token_path.exists():
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)

        # If credentials are not valid, refresh them or create new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not credentials_path.exists():
                    raise FileNotFoundError(
                        f"Credentials file not found for account {account_id}. "
                        f"Please place your OAuth credentials JSON file at {credentials_path}"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials for future use
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

        return creds

    def revoke_credentials(self, account_id: str) -> None:
        """Revoke credentials for the specified account."""
        token_path = self.credentials_dir / f"{account_id}_token.pickle"
        if token_path.exists():
            os.remove(token_path) 