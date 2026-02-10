"""
# src/main.py
# Main entry point for the Gmail Flight Tracker
"""

import argparse
from datetime import datetime, timedelta
import json
import os
from typing import List, Dict
from parsers.flight_parser import parse_flight_email, format_flight_details
from gmail_client import fetch_flight_emails
from storage.email_storage import EmailStorage
import re

def deduplicate_flights(flights: List[Dict]) -> List[Dict]:
    """Remove duplicate flight entries based on key fields"""
    unique_flights = {}
    
    for flight in flights:
        # Create a unique key based on flight details
        key_parts = []
        
        # Required fields for a valid flight entry
        if flight.get('flight_number') and flight.get('departure_datetime'):
            key_parts.extend([
                flight.get('flight_number'),
                flight.get('departure_datetime', '').split('T')[0]
            ])
            
            # Optional fields that help identify unique flights
            key_parts.extend([
                flight.get('departure_airport', ''),
                flight.get('arrival_airport', '')
            ])
            
            key = tuple(key_parts)
            
            # Keep the entry with the most information
            if key not in unique_flights or _count_filled_fields(flight) > _count_filled_fields(unique_flights[key]):
                unique_flights[key] = flight
    
    # Sort flights by departure datetime
    sorted_flights = sorted(
        unique_flights.values(),
        key=lambda x: x.get('departure_datetime', '') or ''
    )
    
    return sorted_flights

def _count_filled_fields(flight: Dict) -> int:
    """Count the number of non-None fields in a flight entry"""
    return sum(1 for value in flight.values() if value is not None)

def process_stored_emails(year: int = None, output_file: str = None, specific_file: str = None) -> List[Dict]:
    """Process stored emails and extract flight information"""
    storage = EmailStorage()
    
    # Load emails from specific file if provided
    emails = storage.load_emails(year, specific_file)
    
    if not emails:
        print(f"No emails found in {specific_file or 'storage'}")
        return []
    
    print(f"\nProcessing {len(emails)} emails...")
    # ... rest of the function remains the same ...

def main():
    parser = argparse.ArgumentParser(description='Gmail Flight Tracker')
    parser.add_argument('--year', type=int, default=datetime.now().year,
                      help='Year to search for flights (default: current year)')
    parser.add_argument('--days', type=int, default=365,
                      help='Number of days to look forward from start of year')
    parser.add_argument('--use-sample', action='store_true',
                      help='Use sample data instead of Gmail API')
    parser.add_argument('--fetch-only', action='store_true',
                      help='Only fetch and store emails, do not process them')
    parser.add_argument('--process-only', action='store_true',
                      help='Only process previously fetched emails')
    args = parser.parse_args()
    
    storage = EmailStorage()
    
    # Handle fetch vs process modes
    if args.fetch_only and args.process_only:
        print("Error: Cannot specify both --fetch-only and --process-only")
        return
        
    # Fetch mode
    if not args.process_only:
        print(f"Loading emails for {args.year} (looking forward {args.days} days from start of year)...")
        
        if args.use_sample:
            # Load sample data
            sample_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'sample')
            if not os.path.exists(sample_dir):
                print(f"Error: Sample directory not found at {sample_dir}")
                return
                
            emails = []
            start_date = datetime(args.year, 1, 1)
            end_date = start_date + timedelta(days=args.days)
            print(f"Looking for emails between {start_date.date()} and {end_date.date()}")
            
            for filename in os.listdir(sample_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(sample_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            email_data = json.load(f)
                            
                            # Parse email date
                            email_date = datetime.strptime(email_data.get('date', ''), '%a, %d %b %Y %H:%M:%S %z')
                            check_date = email_date.astimezone(datetime.now().astimezone().tzinfo)
                            
                            # Check if date is within range
                            if start_date <= check_date <= end_date:
                                print(f"Found matching email: {email_data.get('subject')} (Date: {check_date.date()})")
                                emails.append(email_data)
                    except Exception as e:
                        print(f"Error loading {filename}: {str(e)}")
                        continue
            
            print(f"Found {len(emails)} emails in the specified date range")
        else:
            # Use Gmail API
            emails = fetch_flight_emails(args.year, args.days)
        
        # Save fetched emails
        if emails:
            saved_path = storage.save_emails(emails, args.year)
            print(f"Saved {len(emails)} emails to {saved_path}")
    
    # Process mode
    if not args.fetch_only:
        from process_emails import process_stored_emails
        output_file = f"data/processed/flights_{args.year}.json"
        
        # If process-only, look for most recent email file for the year
        if args.process_only:
            print(f"Processing stored emails for {args.year}...")
            email_files = storage.get_email_files(args.year)
            if not email_files:
                print(f"No stored emails found for {args.year}")
                return
                
            print(f"Found {len(email_files)} email files")
            # Sort by timestamp to get most recent
            latest_file = sorted(email_files)[-1]
            print(f"Processing most recent file: {latest_file}")
        
        flights = process_stored_emails(args.year, output_file, latest_file)
        
        if flights:
            print(f"\nFound {len(flights)} unique flights:\n")
            for i, flight in enumerate(flights, 1):
                print(f"Flight {i}:")
                print("-" * 40)
                print(format_flight_details(flight))
                print()
        else:
            print("\nNo flight information found in the specified date range.")

if __name__ == '__main__':
    main()
