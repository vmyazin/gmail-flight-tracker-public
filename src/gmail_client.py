"""
# src/gmail_client.py
# Gmail API client for fetching flight-related emails
"""

import os
import pickle
from typing import List, Dict
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText
import json

# If modifying these scopes, delete the file token.pickle
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """Get an authorized Gmail API service instance."""
    creds = None
    token_path = os.path.join('credentials', 'token.pickle')
    credentials_path = os.path.join('credentials', 'primary_credentials.json')

    # Load existing token
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # Refresh or create new token if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"Credentials file not found at {credentials_path}. Please ensure the file exists."
                )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the token
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def fetch_flight_emails(year: int, days: int) -> List[Dict]:
    """
    Fetch flight-related emails from Gmail within the specified date range.
    
    Args:
        year: The year to search in
        days: Number of days to look forward from the start of the year
    
    Returns:
        List of email data dictionaries
    """
    service = get_gmail_service()
    
    # Calculate date range
    start_date = datetime(year, 1, 1)
    end_date = start_date + timedelta(days=days)
    
    # Prepare search query
    # Look for common flight-related keywords in subject and common airline domains
    query = (
        f'after:{int(start_date.timestamp())} before:{int(end_date.timestamp())} '
        '(subject:"flight" OR subject:"booking" OR subject:"itinerary" OR subject:"e-ticket" OR '
        'subject:"reservation" OR subject:"travel" OR from:"@vietjetair.com" OR '
        'from:"@trip.com" OR from:"@booking.com" OR from:"@cebuair.com")'
    )
    
    try:
        # Get list of matching messages
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        
        emails = []
        print(f"Found {len(messages)} potential flight emails")
        
        for message in messages:
            # Get full message details
            msg = service.users().messages().get(
                userId='me', id=message['id'], format='full'
            ).execute()
            
            # Extract headers
            headers = msg['payload']['headers']
            email_data = {
                'id': msg['id'],
                'subject': next(
                    (h['value'] for h in headers if h['name'].lower() == 'subject'),
                    'No Subject'
                ),
                'from': next(
                    (h['value'] for h in headers if h['name'].lower() == 'from'),
                    'Unknown Sender'
                ),
                'date': next(
                    (h['value'] for h in headers if h['name'].lower() == 'date'),
                    None
                )
            }
            
            # Extract body
            if 'parts' in msg['payload']:
                parts = msg['payload']['parts']
                for part in parts:
                    if part['mimeType'] == 'text/plain':
                        body = base64.urlsafe_b64decode(
                            part['body']['data'].encode('UTF-8')
                        ).decode('utf-8')
                        email_data['body'] = body
                        break
            elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
                body = base64.urlsafe_b64decode(
                    msg['payload']['body']['data'].encode('UTF-8')
                ).decode('utf-8')
                email_data['body'] = body
            else:
                continue  # Skip if no readable body found
            
            print(f"Found email: {email_data['subject']}")
            emails.append(email_data)
        
        return emails
        
    except Exception as e:
        print(f"Error fetching emails: {str(e)}")
        return [] 