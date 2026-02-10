# src/email_filter.py
import re
from typing import Dict, Optional, List
from dataclasses import dataclass

@dataclass
class FlightBookingMatch:
    """Container for flight booking matches found in email"""
    confirmation_code: str
    flight_numbers: list[str]
    confidence: float

class EmailFilter:
    # Core patterns for reliable flight booking identification
    PATTERNS = {
        # 6-char alphanumeric, must have both letters and numbers, all caps
        'confirmation_code': r'(?<![A-Z0-9])([A-Z0-9]{6})(?![A-Z0-9])',
        
        # Airline code (2 letters) + 3-4 digits, all caps
        'flight_number': r'(?<![A-Z0-9])([A-Z]{2}\d{3,4})(?![A-Z0-9])',
        
        # The word "flight" in any case with context
        'flight_word': r'(?i)(your|my|the|upcoming|scheduled|booked|confirmed|check[\s-]*in|boarding)\s+flight'
    }

    # Known IATA airline codes for validation
    AIRLINE_CODES = {
        'CX', 'SQ', 'MH', 'TR', '3K', '5J', 'PR', 'AK', 'FD', 'VJ', 'QH', 'VN', 'BL'  # Added more Asian carriers
    }

    # Known flight-related email domains
    FLIGHT_DOMAINS = {
        'airasia.com',
        'notification.airasia.com',
        'vietnamairlines.com',
        'vietjetair.com',
        'confirmation.cebu-air.com',
        'philippineairlines.com',
        'singaporeair.com',
        'cathaypacific.com'
    }

    # Excluded terms that indicate non-flight emails
    EXCLUDED_TERMS = {
        'airbnb',
        'booking.com',
        'hotels.com',
        'agoda',
        'expedia'
    }

    @staticmethod
    def is_potential_flight_email(subject: str, body: str, from_address: str) -> bool:
        """
        More precise filtering of flight-related emails.
        Returns True only for emails that are likely to contain flight information.
        """
        # Normalize inputs for consistent matching
        subject_lower = subject.lower()
        from_lower = from_address.lower()
        
        # List of known airline domains and keywords
        airline_domains = {
            'airasia.com', 'vietnamairlines.com', 'united.com', 'delta.com',
            'aa.com', 'emirates.com', 'klm.com', 'lufthansa.com'
        }
        
        # Strong flight indicators in subject
        flight_subject_indicators = {
            'flight confirmation', 'booking confirmation', 'e-ticket',
            'check-in', 'boarding pass', 'flight itinerary', 
            'travel confirmation', 'flight receipt'
        }
        
        # Exclude common false positives
        exclude_keywords = {
            'airbnb', 'booking.com', 'hotels.com', 'expedia',
            'reservation at', 'hotel', 'apartment'
        }
        
        # Check for exclusions first
        if any(excl in subject_lower for excl in exclude_keywords):
            return False
            
        # Check if email is from an airline domain
        if any(domain in from_lower for domain in airline_domains):
            return True
            
        # Check for strong flight indicators in subject
        if any(indicator in subject_lower for indicator in flight_subject_indicators):
            return True
            
        # Look for flight number patterns (e.g., AA123, DL456)
        flight_number_pattern = r'\b[A-Z]{2}\d{3,4}\b'
        if re.search(flight_number_pattern, subject):
            return True
        
        return False

    @staticmethod
    def extract_booking_details(subject: str, body: str) -> Optional[FlightBookingMatch]:
        """Extract booking details using strict pattern matching."""
        full_text = f"{subject}\n{body}"
        
        # Find valid confirmation codes
        confirmation_codes = [
            code.group(1) for code in re.finditer(EmailFilter.PATTERNS['confirmation_code'], full_text)
            if EmailFilter.validate_confirmation_code(code.group(1))
        ]
        
        # Find valid flight numbers
        flight_numbers = [
            num.group(1) for num in re.finditer(EmailFilter.PATTERNS['flight_number'], full_text)
            if EmailFilter.validate_flight_number(num.group(1))
        ]
        
        # Must have at least one valid identifier
        if not (confirmation_codes or flight_numbers):
            return None
            
        # Calculate confidence based on proximity
        confidence = 0.0
        
        # Base confidence from valid identifiers
        if confirmation_codes:
            confidence += 0.4
        if flight_numbers:
            confidence += 0.4
            
        # Check for flight number context
        for flight_num in flight_numbers:
            # Look for "flight" within 50 characters of flight number
            context_pattern = fr'.{{0,50}}(?i)flight.{{0,50}}{flight_num}|{flight_num}.{{0,50}}(?i)flight.{{0,50}}'
            if re.search(context_pattern, full_text):
                confidence += 0.2
                break
                
        if confidence >= 0.6:
            return FlightBookingMatch(
                confirmation_code=confirmation_codes[0] if confirmation_codes else "",
                flight_numbers=flight_numbers,
                confidence=min(1.0, confidence)
            )
        
        return None

    @staticmethod
    def validate_confirmation_code(code: str) -> bool:
        """Strictly validate confirmation code format."""
        if not code or len(code) != 6:
            return False
            
        # Must contain at least one letter and one number
        has_letter = any(c.isalpha() for c in code)
        has_number = any(c.isdigit() for c in code)
        
        # Must be all uppercase
        is_uppercase = code.isupper()
        
        # Must not be all letters or all numbers
        not_all_letters = not code.isalpha()
        not_all_numbers = not code.isdigit()
        
        return all([has_letter, has_number, is_uppercase, not_all_letters, not_all_numbers])

    @staticmethod
    def validate_flight_number(number: str) -> bool:
        """Strictly validate flight number format."""
        if not number or len(number) < 5 or len(number) > 6:
            return False
            
        # Extract airline code and flight number
        match = re.match(r'^([A-Z]{2})(\d{3,4})$', number)
        if not match:
            return False
            
        airline_code = match.group(1)
        flight_digits = match.group(2)
        
        # Validate against known airline codes
        if airline_code not in EmailFilter.AIRLINE_CODES:
            return False
            
        return True 