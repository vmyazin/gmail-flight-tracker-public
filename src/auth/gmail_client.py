"""
# src/auth/gmail_client.py
# Gmail API client wrapper for email operations
"""

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from typing import List, Dict, Any
import base64
import email
import logging
import re
import html

logger = logging.getLogger(__name__)

class GmailClient:
    def __init__(self, credentials: Credentials):
        """Initialize Gmail API client with credentials."""
        logger.info("Initializing Gmail client")
        self.service = build('gmail', 'v1', credentials=credentials)
        logger.debug("Gmail client initialized successfully")

    def search_messages(self, query: str, max_results: int = 500) -> List[Dict[str, Any]]:
        """
        Search for messages matching the query with stricter flight-related criteria.
        """
        try:
            # Strict flight-related terms that must be in subject or body
            required_terms = [
                'flight number',
                'boarding pass',
                'e-ticket',
                'flight confirmation',
                'itinerary',
                'reservation #'
            ]
            
            # Known airline domains and their variations
            airline_domains = [
                'vietjetair.com',
                'airasia.com',
                'vietnamairlines.com',
                'cebu-pacific.com',
                'united.com',
                'delta.com',
                'aa.com',
                'emirates.com'
            ]
            
            # Exclude terms that indicate non-flight content
            exclude_terms = [
                'hotel',
                'booking.com',
                'airbnb',
                'newsletter',
                'promotion',
                'offer',
                'deal',
                'subscribe'
            ]
            
            # Build enhanced query
            enhanced_query = f"({query})"
            enhanced_query += " AND ("
            
            # Add required terms
            subject_terms = " OR ".join(f'subject:"{term}"' for term in required_terms)
            enhanced_query += f"({subject_terms})"
            
            # Add airline domains
            domain_terms = " OR ".join(f'from:@{domain}' for domain in airline_domains)
            enhanced_query += f" OR ({domain_terms})"
            
            # Add exclusions
            exclude_terms = " AND ".join(f'-subject:"{term}"' for term in exclude_terms)
            enhanced_query += f") AND ({exclude_terms})"
            
            logger.debug(f"Enhanced search query: {enhanced_query}")
            
            messages = []
            next_page_token = None
            
            while len(messages) < max_results:
                result = self.service.users().messages().list(
                    userId='me',
                    q=enhanced_query,
                    maxResults=min(max_results - len(messages), 100),
                    pageToken=next_page_token
                ).execute()
                
                if 'messages' in result:
                    # Additional validation of messages
                    for msg_info in result['messages']:
                        msg = self.get_message(msg_info['id'])
                        headers = {
                            header['name'].lower(): header['value'].lower()
                            for header in msg['payload']['headers']
                        }
                        
                        subject = headers.get('subject', '').lower()
                        from_addr = headers.get('from', '').lower()
                        
                        # Skip if from known non-flight sources
                        if any(domain in from_addr for domain in ['booking.com', 'airbnb.com']):
                            logger.debug(f"Skipping non-flight source: {from_addr}")
                            continue
                            
                        # Skip promotional content
                        if any(promo_term in subject for promo_term in ['newsletter', 'offer', 'deal']):
                            logger.debug(f"Skipping promotional content: {subject}")
                            continue
                        
                        # Must have either flight-specific terms or be from airline domain
                        is_flight_related = (
                            any(term.lower() in subject for term in required_terms) or
                            any(domain in from_addr for domain in airline_domains)
                        )
                        
                        if is_flight_related:
                            messages.append(msg_info)
                            logger.debug(f"Including flight-related message: {subject}")
                        else:
                            logger.debug(f"Filtering out non-flight message: {subject}")
                
                if 'nextPageToken' not in result:
                    break
                    
                next_page_token = result['nextPageToken']
                logger.info(f"Fetched {len(messages)} flight-related messages so far...")

            logger.info(f"Found {len(messages)} flight-related messages")
            return messages[:max_results]
            
        except Exception as e:
            logger.error(f"Error searching messages: {e}", exc_info=True)
            return []

    def get_message(self, message_id: str) -> Dict[str, Any]:
        """Get full message details by ID."""
        try:
            logger.debug(f"Fetching message details for ID: {message_id}")
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            logger.debug(f"Successfully fetched message {message_id}")
            return message
        except Exception as e:
            logger.error(f"Error getting message {message_id}: {e}", exc_info=True)
            return {}

    def parse_message_content(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Parse message content into a structured format."""
        try:
            logger.debug("Parsing message content")
            headers = {
                header['name'].lower(): header['value']
                for header in message['payload']['headers']
            }

            parts = []
            if 'parts' in message['payload']:
                parts = message['payload']['parts']
                logger.debug(f"Message has {len(parts)} parts")
            else:
                parts = [message['payload']]
                logger.debug("Message has single part")

            content = {
                'subject': headers.get('subject', ''),
                'from': headers.get('from', ''),
                'date': headers.get('date', ''),
                'body': self._get_message_body(parts)
            }

            logger.debug(f"Successfully parsed message with subject: {content['subject']}")
            return content
        except Exception as e:
            logger.error("Error parsing message content", exc_info=True)
            return {
                'subject': '',
                'from': '',
                'date': '',
                'body': ''
            }

    def _get_message_body(self, parts: List[Dict[str, Any]]) -> str:
        """Extract message body from message parts."""
        text_content = []
        html_content = []
        
        def decode_part(part_body: Dict[str, Any]) -> str:
            """Decode a message part body."""
            if 'data' in part_body:
                try:
                    data = part_body['data']
                    # Fix padding if needed
                    pad_length = 4 - (len(data) % 4)
                    if pad_length != 4:
                        data += '=' * pad_length
                    return base64.urlsafe_b64decode(data.encode('ASCII')).decode('utf-8', errors='replace')
                except Exception as e:
                    logger.warning(f"Error decoding message part: {e}")
                    return ""
            elif 'attachmentId' in part_body:
                logger.debug("Skipping attachment part")
                return ""
            return ""

        def extract_content(part: Dict[str, Any]) -> None:
            """Recursively extract content from message parts."""
            mime_type = part.get('mimeType', '')
            
            if mime_type == 'text/plain':
                text = decode_part(part['body'])
                if text:
                    text_content.append(text)
                    logger.debug("Extracted text/plain content")
            elif mime_type == 'text/html':
                html = decode_part(part['body'])
                if html:
                    html_content.append(html)
                    logger.debug("Extracted text/html content")
            elif mime_type.startswith('multipart/'):
                if 'parts' in part:
                    logger.debug(f"Processing {len(part['parts'])} nested parts")
                    for nested_part in part['parts']:
                        extract_content(nested_part)
        
        try:
            # Process all parts
            for part in parts:
                extract_content(part)
            
            # Prefer plain text if available, otherwise use HTML
            if text_content:
                logger.debug("Using text/plain content")
                return '\n'.join(text_content)
            elif html_content:
                logger.debug("Using text/html content")
                # Basic HTML to text conversion
                html_text = '\n'.join(html_content)
                # Remove HTML tags
                text = re.sub(r'<[^>]+>', ' ', html_text)
                # Fix spacing
                text = re.sub(r'\s+', ' ', text)
                # Convert HTML entities
                text = html.unescape(text)
                return text.strip()
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting message body: {e}", exc_info=True)
            return "" 