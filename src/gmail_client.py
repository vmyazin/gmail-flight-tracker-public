"""
# src/gmail_client.py
# Gmail API client for fetching flight-related emails
"""

import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from googleapiclient.discovery import build
import base64
from auth.google_auth import load_credentials, DEFAULT_SCOPES

# If modifying these scopes, delete the file token.pickle
SCOPES = DEFAULT_SCOPES

def get_gmail_service():
    """Get an authorized Gmail API service instance."""
    token_path = os.path.join('credentials', 'token.pickle')
    credentials_path = os.path.join('credentials', 'primary_credentials.json')

    creds = load_credentials(credentials_path, token_path, SCOPES)

    return build('gmail', 'v1', credentials=creds)

def fetch_flight_emails(
    year: int,
    days: int,
    start_date: Optional[datetime] = None,
    query_mode: str = "strict",
) -> List[Dict]:
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
    if start_date is None:
        start_date = datetime(year, 1, 1)
    end_date = start_date + timedelta(days=days)
    
    # Prepare search query
    if query_mode == "relaxed":
        query = f'after:{int(start_date.timestamp())} before:{int(end_date.timestamp())} in:inbox'
    else:
        # Look for common flight-related keywords in subject and common airline domains
        query = (
            f'after:{int(start_date.timestamp())} before:{int(end_date.timestamp())} '
            '(subject:"flight" OR subject:"booking" OR subject:"itinerary" OR subject:"e-ticket" OR '
            'subject:"reservation" OR subject:"travel" OR from:"@vietjetair.com" OR '
            'from:"@trip.com" OR from:"@booking.com" OR from:"@cebuair.com")'
        )
    
    try:
        emails = []
        total_messages = 0
        next_page_token = None

        while True:
            list_kwargs = {"userId": "me", "q": query}
            if next_page_token:
                list_kwargs["pageToken"] = next_page_token
            results = service.users().messages().list(**list_kwargs).execute()

            messages = results.get('messages', [])
            total_messages += len(messages)

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

            next_page_token = results.get('nextPageToken')
            if not next_page_token:
                break

        print(f"Found {total_messages} potential flight emails")
        return emails
        
    except Exception as e:
        print(f"Error fetching emails: {str(e)}")
        return [] 
