"""
# src/auth/google_auth.py
# Handles Google OAuth2 authentication and token management
"""

import os
import pickle
from pathlib import Path
from typing import Optional, Sequence
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

DEFAULT_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def load_credentials(
    credentials_path: str,
    token_path: str,
    scopes: Optional[Sequence[str]] = None,
) -> Credentials:
    """Load and refresh credentials for a given credentials/token path pair."""
    creds = None
    scopes = list(scopes) if scopes is not None else DEFAULT_SCOPES
    token_file = Path(token_path)
    credentials_file = Path(credentials_path)

    if token_file.exists():
        with token_file.open('rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError as exc:
                # Refresh tokens can be revoked/expired; fall back to full auth.
                print(f"Token refresh failed ({exc}). Re-authentication required.")
                creds = None
                if token_file.exists():
                    token_file.unlink()
        if not creds or not creds.valid:
            if not credentials_file.exists():
                raise FileNotFoundError(
                    f"Credentials file not found at {credentials_file}. Please ensure the file exists."
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_file), scopes
            )
            creds = flow.run_local_server(port=0)

        token_file.parent.mkdir(exist_ok=True)
        with token_file.open('wb') as token:
            pickle.dump(creds, token)

    return creds

class GoogleAuthManager:
    def __init__(self, credentials_dir: str = "credentials"):
        self.credentials_dir = Path(credentials_dir)
        self.credentials_dir.mkdir(exist_ok=True)
        
    def get_credentials(self, account_id: str) -> Credentials:
        """Get valid credentials for the specified account."""
        token_path = self.credentials_dir / f"{account_id}_token.pickle"
        credentials_path = self.credentials_dir / f"{account_id}_credentials.json"
        return load_credentials(str(credentials_path), str(token_path), DEFAULT_SCOPES)

    def revoke_credentials(self, account_id: str) -> None:
        """Revoke credentials for the specified account."""
        token_path = self.credentials_dir / f"{account_id}_token.pickle"
        if token_path.exists():
            os.remove(token_path) 
