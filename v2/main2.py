"""
# v2/main2.py
# Main entry point for Gmail Flight Tracker v2
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from tqdm import tqdm
import re

# Add root directory to path for importing root modules
root_dir = str(Path(__file__).parent.parent)
sys.path.append(root_dir)

from src.auth.google_auth import GoogleAuthManager
from src.auth.gmail_client import GmailClient

class GmailFlightTracker:
    def __init__(self, config):
        self.config = {
            'credentials': config['credentials'],
            'searchDepthDays': config.get('searchDepthDays', 365),
            'batchSize': config.get('batchSize', 100)
        }
        
        # Updated patterns to focus on most reliable identifiers
        self.patterns = {
            # 6-character alphanumeric confirmation code
            'confirmationCode': r'(?:(?:confirmation|booking|reference|pnr|reservation)(?:\s+(?:code|number|#|no|id))?\s*[:# ]*)([A-Z0-9]{6})(?!\w)',
            
            # Airline code + flight number (more specific pattern)
            'flightNumber': r'(?:flight(?:\s+(?:number|#|no))?\s*[:# ]*)?([A-Z]{2})\s*(\d{1,4})(?!\d)',
            
            # The word "flight" and its context
            'flightContext': r'(?i)(?:flight|boarding|departure|arrival)',
            
            # Additional patterns for context validation
            'date': r'(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4}|\d{4}-\d{2}-\d{2})',
            'airport': r'([A-Z]{3})'
        }
        
        self.gmail_client = None

    def initialize(self):
        """Initialize the Gmail client."""
        try:
            self.gmail_client = GmailClient(self.config['credentials'])
            return True
        except Exception as e:
            print(f"Failed to initialize Gmail client: {e}")
            return False

    def searchFlightEmails(self, start_date, end_date):
        """Search for flight-related emails within the date range."""
        query = self._buildSearchQuery(start_date, end_date)
        return self.gmail_client.search_messages(query, max_results=self.config['batchSize'])

    def _buildSearchQuery(self, start_date, end_date):
        """Build the Gmail search query."""
        return (
            f"(from:(*airlines* OR *booking* OR *travel*) OR "
            f"subject:(\"flight confirmation\" OR itinerary OR \"e-ticket\")) "
            f"after:{start_date.strftime('%Y/%m/%d')} "
            f"before:{end_date.strftime('%Y/%m/%d')}"
        )

    def processEmails(self, emails):
        """Process emails to extract flight information."""
        flights = []
        for email in tqdm(emails, desc="Processing emails"):
            flight_info = self._extractFlightInfo(email)
            if flight_info:
                flights.append(flight_info)
                # Print debug info for confirmed flights
                print(f"\nFound flight: {flight_info.get('flightNumber', 'Unknown')} "
                      f"(Confidence: {flight_info['confidence']:.2f})")
                if 'confirmationCode' in flight_info:
                    print(f"Confirmation Code: {flight_info['confirmationCode']}")
        
        return self._deduplicateFlights(flights)

    def _extractFlightInfo(self, email):
        """Extract flight information from an email with focus on reliable patterns."""
        try:
            # Get full message if needed
            if 'payload' not in email:
                email = self.gmail_client.get_message(email['id'])
            
            # Extract headers and content
            headers = {}
            if 'payload' in email and 'headers' in email['payload']:
                headers = {
                    header['name'].lower(): header['value']
                    for header in email['payload']['headers']
                }
            
            subject = headers.get('subject', '')
            from_addr = headers.get('from', '')
            snippet = email.get('snippet', '')
            
            # Combine text sources for pattern matching
            full_text = f"{subject}\n{snippet}"
            
            # Initialize flight info with basic metadata
            flight_info = {
                'id': email['id'],
                'threadId': email['threadId'],
                'date': email.get('internalDate'),
                'subject': subject,
                'from': from_addr,
                'confidence': 0.0
            }
            
            # Look for confirmation code
            conf_match = re.search(self.patterns['confirmationCode'], full_text, re.IGNORECASE)
            if conf_match:
                flight_info['confirmationCode'] = conf_match.group(1)
                flight_info['confidence'] += 0.4  # High confidence for confirmation code
            
            # Look for flight number
            flight_match = re.search(self.patterns['flightNumber'], full_text)
            if flight_match:
                airline_code = flight_match.group(1)
                flight_num = flight_match.group(2)
                flight_info['flightNumber'] = f"{airline_code}{flight_num}"
                flight_info['airline'] = airline_code
                flight_info['confidence'] += 0.4  # High confidence for flight number
            
            # Check for flight context words
            flight_context_matches = re.findall(self.patterns['flightContext'], full_text, re.IGNORECASE)
            if flight_context_matches:
                flight_info['confidence'] += min(0.1 * len(flight_context_matches), 0.2)  # Up to 0.2 for context
            
            # Only return flights with sufficient confidence
            if flight_info['confidence'] >= 0.4:  # At least one major identifier
                # Add debug information
                flight_info['debug'] = {
                    'hasConfirmationCode': 'confirmationCode' in flight_info,
                    'hasFlightNumber': 'flightNumber' in flight_info,
                    'flightContextCount': len(flight_context_matches) if flight_context_matches else 0
                }
                return flight_info
            
            return None
            
        except Exception as e:
            print(f"Warning: Error extracting flight info from email {email.get('id')}: {str(e)}")
            return None

    def _deduplicateFlights(self, flights):
        """Remove duplicate flight entries."""
        seen = set()
        unique_flights = []
        
        for flight in flights:
            flight_key = f"{flight.get('id')}-{flight.get('threadId')}"
            if flight_key not in seen:
                seen.add(flight_key)
                unique_flights.append(flight)
        
        return unique_flights

    def generateStatistics(self, flights):
        """Generate statistics from processed flights."""
        return {
            'totalFlights': len(flights),
            'uniqueAirlines': len(set(flight.get('airline', '') for flight in flights)),
            'flightsByMonth': self._groupFlightsByMonth(flights),
            'mostFrequentRoute': self._findMostFrequentRoute(flights)
        }

    def _groupFlightsByMonth(self, flights):
        """Group flights by month."""
        months = {}
        for flight in flights:
            try:
                if 'date' in flight and flight['date']:
                    # Convert string to int if it's a string
                    timestamp = (
                        int(flight['date']) 
                        if isinstance(flight['date'], (int, str)) 
                        else None
                    )
                    
                    if timestamp:
                        month = datetime.fromtimestamp(timestamp/1000).strftime('%B')
                        if month not in months:
                            months[month] = []
                        months[month].append(flight)
                    else:
                        print(f"Warning: Invalid date format for flight: {flight.get('id')}")
            except (ValueError, TypeError) as e:
                print(f"Warning: Could not process date for flight: {flight.get('id')} - {str(e)}")
                continue
        return months

    def _findMostFrequentRoute(self, flights):
        """Find the most frequent route."""
        routes = {}
        most_frequent = None
        max_count = 0
        
        for flight in flights:
            route = f"{flight.get('departure', '')}-{flight.get('arrival', '')}"
            routes[route] = routes.get(route, 0) + 1
            
            if routes[route] > max_count:
                max_count = routes[route]
                most_frequent = (route, max_count)
        
        return most_frequent

def setup_tracker(account_id: str = "primary"):
    """Initialize the flight tracker with credentials from root."""
    auth_manager = GoogleAuthManager(credentials_dir=os.path.join(root_dir, "credentials"))
    credentials = auth_manager.get_credentials(account_id)
    
    tracker = GmailFlightTracker({
        'credentials': credentials,
        'searchDepthDays': 365,
        'batchSize': 100
    })
    
    return tracker

def main():
    parser = argparse.ArgumentParser(description='Gmail Flight Tracker v2')
    parser.add_argument('--year', type=int, default=datetime.now().year,
                      help='Year to search for flights (default: current year)')
    parser.add_argument('--days', type=int, default=365,
                      help='Number of days to look forward')
    parser.add_argument('--account', type=str, default="primary",
                      help='Account ID to use from credentials')
    args = parser.parse_args()
    
    try:
        # Initialize tracker
        tracker = setup_tracker(args.account)
        if not tracker.initialize():
            print("Failed to initialize tracker")
            return
        
        # Set date range
        start_date = datetime(args.year, 1, 1)
        end_date = start_date + timedelta(days=args.days)
        
        print(f"Searching for flights between {start_date.date()} and {end_date.date()}")
        
        # Search and process emails
        emails = tracker.searchFlightEmails(start_date, end_date)
        if not emails:
            print("No flight emails found")
            return
            
        print(f"Found {len(emails)} potential flight emails")
        
        # Process emails and extract flight information
        flights = tracker.processEmails(emails)
        if not flights:
            print("No flight information extracted")
            return
            
        print(f"\nExtracted {len(flights)} flights:")
        
        # Generate statistics
        stats = tracker.generateStatistics(flights)
        
        # Output results
        print("\nFlight Statistics:")
        print(f"Total Flights: {stats['totalFlights']}")
        print(f"Unique Airlines: {stats['uniqueAirlines']}")
        if stats['mostFrequentRoute']:
            route, count = stats['mostFrequentRoute']
            print(f"Most Frequent Route: {route} ({count} times)")
        
        print("\nFlights by Month:")
        for month, month_flights in stats['flightsByMonth'].items():
            print(f"{month}: {len(month_flights)} flights")
        
        # Save results
        output_dir = os.path.join(root_dir, "data", "processed")
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = os.path.join(output_dir, f"flights_{args.year}.json")
        with open(output_file, 'w') as f:
            json.dump({
                'flights': flights,
                'statistics': stats
            }, f, indent=2)
        
        print(f"\nResults saved to {output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return

if __name__ == '__main__':
    main()