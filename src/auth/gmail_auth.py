"""
# src/auth/gmail_auth.py
# Backwards-compatible Gmail authentication wrapper.
"""

from typing import Optional, Sequence
from googleapiclient.discovery import build
from .google_auth import load_credentials, DEFAULT_SCOPES


class GmailAuthenticator:
    """Legacy wrapper around shared Google auth helpers."""

    def __init__(
        self,
        credentials_path: str,
        token_path: str,
        scopes: Optional[Sequence[str]] = None,
    ) -> None:
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.scopes = list(scopes) if scopes is not None else DEFAULT_SCOPES

    def get_service(self):
        creds = load_credentials(self.credentials_path, self.token_path, self.scopes)
        return build('gmail', 'v1', credentials=creds)
