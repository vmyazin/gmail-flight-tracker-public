from .email_filter import EmailFilter
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_emails(messages: List[Dict]) -> List[Dict]:
    """
    Process email messages and filter for flight bookings.
    
    Args:
        messages: List of email messages with subject, body, and from_address
        
    Returns:
        List of filtered messages with booking details
    """
    # Initial quick filtering
    potential_flight_emails = [
        msg for msg in messages 
        if EmailFilter.is_potential_flight_email(
            msg.get('subject', ''), 
            msg.get('body', '')
        )
    ]
    
    logger.info(f"Found {len(potential_flight_emails)} potential flight emails out of {len(messages)} total emails")
    
    filtered_messages = []
    
    # Detailed processing of potential flight emails
    for message in potential_flight_emails:
        subject = message.get('subject', '')
        body = message.get('body', '')
        
        booking_match = EmailFilter.extract_booking_details(subject, body)
        
        if booking_match:
            valid_confirmation = (not booking_match.confirmation_code or 
                                EmailFilter.validate_confirmation_code(booking_match.confirmation_code))
            valid_flights = any(EmailFilter.validate_flight_number(num) 
                              for num in booking_match.flight_numbers)
            
            if valid_confirmation or valid_flights:
                filtered_messages.append({
                    'message': message,
                    'booking_details': {
                        'confirmation_code': booking_match.confirmation_code,
                        'flight_numbers': booking_match.flight_numbers,
                    },
                    'confidence': booking_match.confidence
                })
                logger.info(f"Found booking: {booking_match.confirmation_code or booking_match.flight_numbers[0]}")
    
    logger.info(f"Confirmed {len(filtered_messages)} actual flight bookings")
    return filtered_messages 