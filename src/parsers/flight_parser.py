"""
# src/parsers/flight_parser.py
# Parser for extracting flight information from emails
"""

import re
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional

# Add logging configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@dataclass
class FlightInfo:
    flight_number: str
    departure_datetime: str
    arrival_datetime: str
    departure_airport: str
    arrival_airport: str
    confirmation_code: str
    airline: str
    
    def to_dict(self) -> Dict:
        return {
            'flight_number': self.flight_number,
            'departure_datetime': self.departure_datetime,
            'arrival_datetime': self.arrival_datetime,
            'departure_airport': self.departure_airport,
            'arrival_airport': self.arrival_airport,
            'confirmation_code': self.confirmation_code,
            'airline': self.airline
        }

def parse_flight_email(email: Dict) -> Optional[FlightInfo]:
    """Extract flight information from email content"""
    subject = email.get('subject', '')
    body = email.get('body', '')
    from_addr = email.get('from', '')
    
    logger.debug(f"Processing email with subject: {subject}")
    logger.debug(f"From address: {from_addr}")
    
    # Detect airline from subject and body
    airline = _detect_airline(subject, body, from_addr)
    logger.debug(f"Detected airline: {airline}")
    
    # Try airline-specific parser first
    if airline == 'VietJet Air':
        logger.debug("Using VietJet Air parser")
        result = _parse_vietjet_email(subject, body)
        if result:
            return result
    
    # Try generic parser if airline-specific parser fails
    logger.debug("Using generic parser")
    return _parse_generic_email(subject, body, from_addr)

def _detect_airline(subject: str, body: str, from_addr: str) -> str:
    """Detect airline from email content"""
    # Check subject first
    airline_keywords = {
        'VietJet Air': ['vietjet', 'vjet'],
        'AirAsia': ['airasia', 'air asia'],
        'Vietnam Airlines': ['vietnam airlines'],
        'Cebu Pacific': ['cebu pacific']
    }
    
    combined_text = f"{subject} {body}".lower()
    
    for airline, keywords in airline_keywords.items():
        if any(keyword in combined_text for keyword in keywords):
            return airline
            
    # Check email domains as fallback
    airline_domains = {
        'vietjetair.com': 'VietJet Air',
        'airasia.com': 'AirAsia',
        'vietnamairlines.com': 'Vietnam Airlines',
        'cebu-pacific.com': 'Cebu Pacific'
    }
    
    for domain, airline in airline_domains.items():
        if domain in from_addr.lower():
            return airline
    
    return 'Unknown Airline'

def _parse_vietjet_email(subject: str, body: str) -> Optional[FlightInfo]:
    """Parse VietJet Air specific email format"""
    # More flexible reservation pattern
    reservation_patterns = [
        r'Reservation\s*#?\s*([A-Z0-9]+)',
        r'Booking\s*(?:number|#)?\s*([A-Z0-9]+)',
    ]
    
    confirmation_code = None
    for pattern in reservation_patterns:
        match = re.search(pattern, subject + ' ' + body, re.IGNORECASE)
        if match:
            confirmation_code = match.group(1)
            logger.debug(f"Found confirmation code: {confirmation_code}")
            break
    
    # More flexible flight number patterns
    flight_patterns = [
        r'Flight\s*(?:No\.|Number)?\s*([A-Z]{2}\s*\d{3,4})',
        r'([A-Z]{2}\s*\d{3,4})',
    ]
    
    flight_number = None
    for pattern in flight_patterns:
        match = re.search(pattern, body)
        if match:
            flight_number = match.group(1).replace(' ', '')
            logger.debug(f"Found flight number: {flight_number}")
            break
    
    # More flexible airport patterns
    airport_patterns = [
        r'(?:From|Departure):\s*([A-Z]{3})\s+(?:To|Arrival):\s*([A-Z]{3})',
        r'([A-Z]{3})\s*(?:to|→)\s*([A-Z]{3})',
        r'([A-Z]{3})[^A-Z]{1,20}([A-Z]{3})',
    ]
    
    departure_airport = arrival_airport = None
    for pattern in airport_patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            departure_airport = match.group(1)
            arrival_airport = match.group(2)
            logger.debug(f"Found airports: {departure_airport} -> {arrival_airport}")
            break
    
    # More flexible date patterns
    date_patterns = [
        r'(?:Date|Departure):\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})',
        r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})',
        r'(\d{2}/\d{2}/\d{4})',
    ]
    
    departure_date = None
    for pattern in date_patterns:
        match = re.search(pattern, body)
        if match:
            departure_date = match.group(1)
            logger.debug(f"Found date: {departure_date}")
            break
    
    if flight_number and departure_airport and arrival_airport:
        return FlightInfo(
            flight_number=flight_number,
            departure_datetime=departure_date or '',
            arrival_datetime='',  # Will implement arrival time extraction
            departure_airport=departure_airport,
            arrival_airport=arrival_airport,
            confirmation_code=confirmation_code or '',
            airline='VietJet Air'
        )
    else:
        logger.debug("Missing required fields for VietJet Air parser")
        logger.debug(f"Flight number: {flight_number}")
        logger.debug(f"Departure airport: {departure_airport}")
        logger.debug(f"Arrival airport: {arrival_airport}")
    
    return None

def _parse_generic_email(subject: str, body: str, from_addr: str) -> Optional[FlightInfo]:
    """Parse generic flight confirmation email"""
    # Add more common patterns for third-party booking services
    flight_patterns = [
        r'(?:Flight|Flight\s+Number):\s*([A-Z]{2}\s*\d{3,4})',
        r'([A-Z]{2}\s*\d{3,4})\s+(?:to|→)',
        r'Flight:\s*([A-Z]{2}\s*\d{3,4})',
        r'Flight\s+([A-Z]{2}\s*\d{3,4})',
    ]
    
    airport_patterns = [
        r'([A-Z]{3})\s*(?:to|→)\s*([A-Z]{3})',
        r'Departure:\s*([A-Z]{3}).*Arrival:\s*([A-Z]{3})',
        r'From\s*:\s*([A-Z]{3})[^A-Z]*To\s*:\s*([A-Z]{3})',
        r'(?:From|Departure)[^A-Z]*([A-Z]{3})[^A-Z]*(?:To|Arrival)[^A-Z]*([A-Z]{3})',
    ]
    
    confirmation_patterns = [
        r'(?:Confirmation|Booking|Reference|PNR|Reservation)(?:\s+(?:Code|Number|#))?\s*[:# ]\s*([A-Z0-9]{5,8})',
        r'#\s*([A-Z0-9]{5,8})',
    ]
    
    # Try to extract information using patterns
    flight_number = None
    for pattern in flight_patterns:
        match = re.search(pattern, body + ' ' + subject, re.IGNORECASE)
        if match:
            flight_number = match.group(1).replace(' ', '')
            logger.debug(f"Found flight number: {flight_number}")
            break
    
    airports = None
    for pattern in airport_patterns:
        match = re.search(pattern, body + ' ' + subject, re.IGNORECASE)
        if match:
            airports = (match.group(1), match.group(2))
            logger.debug(f"Found airports: {airports[0]} -> {airports[1]}")
            break
    
    confirmation = None
    for pattern in confirmation_patterns:
        match = re.search(pattern, body + ' ' + subject, re.IGNORECASE)
        if match:
            confirmation = match.group(1)
            logger.debug(f"Found confirmation: {confirmation}")
            break
    
    airline = _detect_airline(subject, body, from_addr)
    
    if flight_number and airports:
        return FlightInfo(
            flight_number=flight_number,
            departure_datetime='',  # Need to implement date extraction
            arrival_datetime='',
            departure_airport=airports[0],
            arrival_airport=airports[1],
            confirmation_code=confirmation or '',
            airline=airline
        )
    
    logger.debug("Missing required fields in generic parser")
    logger.debug(f"Flight number: {flight_number}")
    logger.debug(f"Airports: {airports}")
    return None

def format_flight_details(flight: Dict) -> str:
    """Format flight details for display"""
    return f"""Flight: {flight['flight_number']}
Airline: {flight['airline']}
From: {flight['departure_airport']}
To: {flight['arrival_airport']}
Departure: {flight['departure_datetime']}
Confirmation: {flight['confirmation_code']}"""

