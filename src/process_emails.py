"""
# src/process_emails.py
# Script for processing stored emails and extracting flight information
"""

import argparse
from datetime import datetime
import json
import os
from typing import List, Dict
from storage.email_storage import EmailStorage
from parsers.flight_parser import parse_flight_email, format_flight_details
from main import deduplicate_flights

def process_stored_emails(year: int = None, output_file: str = None, specific_file: str = None) -> List[Dict]:
    """
    Process stored emails and extract flight information
    
    Args:
        year: Optional year to filter emails by
        output_file: Optional path to save results to
        specific_file: Optional specific file to process
        
    Returns:
        List of extracted flight information dictionaries
    """
    # Load emails from storage
    storage = EmailStorage()
    emails = storage.load_emails(year, specific_file)
    
    if not emails:
        print(f"No emails found in {specific_file or ('year ' + str(year) if year else 'storage')}")
        return []
    
    print(f"\nProcessing {len(emails)} emails...")
    flight_info_list = []
    
    for email in emails:
        print(f"\nProcessing email: {email.get('subject')}")
        flight_info = parse_flight_email(email)
        if flight_info:
            flight_dict = flight_info.to_dict()
            print("Extracted flight info:")
            print(format_flight_details(flight_dict))
            flight_info_list.append(flight_dict)
        else:
            print("No flight information extracted")
    
    # Remove duplicates
    flights = deduplicate_flights(flight_info_list)
    
    if flights:
        print(f"\nFound {len(flights)} unique flights")
        
        # Save results if output file specified
        if output_file:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'metadata': {
                        'process_date': datetime.now().isoformat(),
                        'year': year,
                        'email_count': len(emails),
                        'flight_count': len(flights)
                    },
                    'flights': flights
                }, f, indent=2, ensure_ascii=False)
            print(f"\nResults saved to {output_file}")
    else:
        print("\nNo flight information found in the stored emails.")
    
    return flights

def main():
    parser = argparse.ArgumentParser(description='Process stored emails to extract flight information')
    parser.add_argument('--year', type=int, help='Year to process emails for (default: all years)')
    parser.add_argument('--output', type=str, help='Path to save results to (default: data/processed/flights_YYYY.json)')
    args = parser.parse_args()
    
    # If no output file specified, use default
    if not args.output and args.year:
        args.output = f"data/processed/flights_{args.year}.json"
    elif not args.output:
        args.output = f"data/processed/flights_all.json"
    
    process_stored_emails(args.year, args.output)

if __name__ == '__main__':
    main() 