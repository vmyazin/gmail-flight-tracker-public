import json
from datetime import datetime
from typing import Dict, List
from src.email_filter import EmailFilter

# ANSI color codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
RESET = '\033[0m'

class EmailFetcher:
    def __init__(self):
        self.email_filter = EmailFilter()
        self.processed_ids = set()  # Cache of processed email IDs
        
    def fetch_and_filter_emails(self, raw_emails: List[Dict]) -> List[Dict]:
        """
        Filter emails during fetch process using strict validation.
        Only saves emails that pass our core flight email criteria.
        """
        filtered_emails = []
        total_count = len(raw_emails)
        flight_related_count = 0
        
        # Skip already processed emails
        new_emails = [email for email in raw_emails 
                     if email.get('id') not in self.processed_ids]

        for email in new_emails:
            try:
                subject = email.get('subject', '')
                body = email.get('body', '')
                from_address = email.get('from', '')

                # Apply strict validation during fetch
                is_potential = self.email_filter.is_potential_flight_email(
                    subject, body, from_address
                )
                
                if is_potential:
                    print(f"{YELLOW}Potential flight email found: {subject}{RESET}")
                    # Extract booking details to further validate
                    booking_details = self.email_filter.extract_booking_details(
                        subject, body
                    )
                    
                    if booking_details and booking_details.confidence >= 0.6:
                        flight_related_count += 1
                        filtered_emails.append(self._prepare_email_data(
                            email, booking_details
                        ))
                        self._log_confirmed_booking(
                            subject, from_address, booking_details
                        )
                
                # Cache processed email ID
                self.processed_ids.add(email.get('id'))
                
            except Exception as e:
                print(f"Error processing email {email.get('id')}: {str(e)}")
                continue

        print(f"Found {flight_related_count} flight-related emails out of {total_count} total emails")
        return filtered_emails

    def _prepare_email_data(self, email: Dict, booking_details) -> Dict:
        """Prepare email data with booking details for storage."""
        return {
            **email,
            'booking_details': {
                'confirmation_code': booking_details.confirmation_code,
                'flight_numbers': booking_details.flight_numbers,
                'confidence': booking_details.confidence
            }
        }

    def _log_confirmed_booking(self, subject: str, from_address: str, booking_details) -> None:
        """Log confirmed booking details."""
        print(f"{GREEN}Confirmed flight booking:{RESET}")
        print(f"  Subject: {subject}")
        print(f"  From: {from_address}")
        print(f"  Confirmation: {booking_details.confirmation_code}")
        print(f"  Flight Numbers: {', '.join(booking_details.flight_numbers)}")
        print(f"  Confidence: {booking_details.confidence}")
        print("-" * 80)

    def save_filtered_emails(self, filtered_emails: List[Dict], year: int) -> None:
        """Save only the filtered emails that passed validation."""
        if not filtered_emails:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/raw_emails/emails_{year}_{timestamp}.json"
        
        output = {
            "metadata": {
                "fetch_date": datetime.now().isoformat(),
                "year": year,
                "email_count": len(filtered_emails)
            },
            "emails": filtered_emails
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"Saved {len(filtered_emails)} filtered emails to {filename}") 