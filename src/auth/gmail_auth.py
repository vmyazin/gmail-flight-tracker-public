# src/auth/gmail_auth.py
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle

class GmailAuthenticator:
    def __init__(self, credentials_path: str, token_path: str):
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
        self.credentials_path = credentials_path
        self.token_path = token_path

    def get_service(self):
        creds = self._load_or_refresh_credentials()
        return build('gmail', 'v1', credentials=creds)

    def _load_or_refresh_credentials(self):
        creds = None
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return creds

# src/auth/account_manager.py
import json
from dataclasses import dataclass
from typing import List, Dict
from ..utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class AccountConfig:
    name: str
    credentials_path: str

class AccountManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.accounts: List[AccountConfig] = []
        self._load_config()

    def _load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.accounts = [
                    AccountConfig(**account) 
                    for account in config['accounts']
                ]
        except Exception as e:
            logger.error(f"Failed to load account config: {e}")
            raise

# src/parsers/email_parser.py
from typing import Dict, Any
import base64
import email

class EmailParser:
    def __init__(self, service):
        self.service = service

    def get_email_content(self, msg_id: str) -> Dict[str, Any]:
        message = self.service.users().messages().get(
            userId='me', id=msg_id, format='full').execute()
        
        payload = message['payload']
        headers = payload.get('headers', [])
        
        return {
            'subject': self._get_header(headers, 'subject'),
            'date': self._get_header(headers, 'date'),
            'body': self._get_body(payload)
        }

    def _get_header(self, headers: List[Dict], name: str) -> str:
        return next(
            (h['value'] for h in headers if h['name'].lower() == name.lower()),
            ''
        )

    def _get_body(self, payload: Dict) -> str:
        if 'body' in payload and 'data' in payload['body']:
            return base64.urlsafe_b64decode(
                payload['body']['data'].encode('ASCII')
            ).decode('utf-8')
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    return base64.urlsafe_b64decode(
                        part['body']['data'].encode('ASCII')
                    ).decode('utf-8')
        
        return ''

# src/parsers/flight_extractor.py
import re
from typing import Dict, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)

class FlightExtractor:
    def __init__(self):
        self.patterns = {
            'flight_number': r'Flight\s*(?:Number|#)?\s*:?\s*([A-Z]{2,3}\s*\d{1,4})',
            'departure': r'Departure:\s*([^|\n]+)',
            'arrival': r'Arrival:\s*([^|\n]+)',
            'date': r'Date:\s*([^|\n]+)',
            'departure_time': r'Departure Time:\s*([^|\n]+)',
            'arrival_time': r'Arrival Time:\s*([^|\n]+)'
        }

    def extract_flight_info(self, email_content: Dict) -> Optional[Dict]:
        try:
            full_text = f"{email_content['subject']}\n{email_content['body']}"
            flight_info = {}
            
            for key, pattern in self.patterns.items():
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    flight_info[key] = match.group(1).strip()
            
            return flight_info if flight_info else None
            
        except Exception as e:
            logger.error(f"Error extracting flight info: {e}")
            return None

# src/exporters/csv_exporter.py
import pandas as pd
from typing import List, Dict
from ..utils.logger import get_logger

logger = get_logger(__name__)

class CSVExporter:
    def __init__(self, output_path: str):
        self.output_path = output_path

    def export(self, flights: List[Dict]) -> bool:
        try:
            df = pd.DataFrame(flights)
            df.to_csv(self.output_path, index=False)
            logger.info(f"Exported {len(flights)} flights to {self.output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export flights to CSV: {e}")
            return False

# src/utils/logger.py
import logging
import os
from datetime import datetime

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # File handler
        file_handler = logging.FileHandler(
            f'logs/app_{datetime.now().strftime("%Y%m%d")}.log'
        )
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger

# src/utils/error_handler.py
from functools import wraps
from typing import Callable
from .logger import get_logger

logger = get_logger(__name__)

def handle_errors(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise
    return wrapper

# src/main.py
import os
from auth.account_manager import AccountManager
from auth.gmail_auth import GmailAuthenticator
from parsers.email_parser import EmailParser
from parsers.flight_extractor import FlightExtractor
from exporters.csv_exporter import CSVExporter
from utils.logger import get_logger
from utils.error_handler import handle_errors

logger = get_logger(__name__)

@handle_errors
def main():
    # Initialize account manager
    account_manager = AccountManager('config/accounts.json')
    
    all_flights = []
    
    # Process each account
    for account in account_manager.accounts:
        logger.info(f"Processing account: {account.name}")
        
        # Initialize authentication
        auth = GmailAuthenticator(
            account.credentials_path,
            f"credentials/token_{account.name}.pickle"
        )
        service = auth.get_service()
        
        # Initialize parsers
        email_parser = EmailParser(service)
        flight_extractor = FlightExtractor()
        
        # TODO: Implement email search and processing
        # This is where you'll add the email search and processing logic
        
    # Export results
    if all_flights:
        exporter = CSVExporter('data/flights.csv')
        exporter.export(all_flights)
        logger.info(f"Exported {len(all_flights)} flights")
    else:
        logger.info("No flights found")

if __name__ == "__main__":
    main()