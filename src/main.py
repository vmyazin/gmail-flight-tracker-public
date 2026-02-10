"""
# src/main.py
# Main entry point for the Gmail Flight Tracker
"""

import argparse
from datetime import datetime, timedelta
import json
import os
from typing import List, Dict, Optional

from dotenv import load_dotenv
from parsers.flight_parser import format_flight_details
from gmail_client import fetch_flight_emails
from storage.email_storage import EmailStorage

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

def _env_float(name: str) -> Optional[float]:
    value = os.getenv(name)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_start_date(year: int, start_date: str) -> Optional[datetime]:
    try:
        month_str, day_str = start_date.split("-", 1)
        month = int(month_str)
        day = int(day_str)
        return datetime(year, month, day)
    except Exception:
        return None


def _get_llm_api_key() -> Optional[str]:
    return os.getenv("OPENAI_API_KEY")


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description='Gmail Flight Tracker')
    parser.add_argument('--year', type=int, default=datetime.now().year,
                      help='Year to search for flights (default: current year)')
    parser.add_argument('--days', type=int, default=365,
                      help='Number of days to look forward from start date')
    parser.add_argument('--start-date', type=str, default='01-01',
                      help='Start date to look forward from, MM-DD (default: 01-01)')
    parser.add_argument('--use-sample', action='store_true',
                      help='Use sample data instead of Gmail API')
    parser.add_argument('--fetch-only', action='store_true',
                      help='Only fetch and store emails, do not process them')
    parser.add_argument('--process-only', action='store_true',
                      help='Only process previously fetched emails')
    parser.add_argument('--use-llm', action='store_true',
                      help='Use LLM extraction when regex parsing fails')
    parser.add_argument('--llm-filter', action='store_true',
                      help='Use LLM to filter itinerary-related emails before parsing')
    parser.add_argument('--llm-filter-threshold', type=float, default=0.6,
                      help='Confidence threshold to skip non-itinerary emails (default: 0.6)')
    parser.add_argument('--llm-filter-max-body-chars', type=int, default=None,
                      help='Max body chars for LLM filter (default: use --llm-max-body-chars)')
    parser.add_argument('--llm-filter-output-tokens', type=int, default=60,
                      help='Expected output tokens for LLM filter (default: 60)')
    parser.add_argument('--llm-model', type=str, default='gpt-5-mini',
                      help='LLM model to use (default: gpt-5-mini)')
    parser.add_argument('--llm-max-body-chars', type=int, default=4000,
                      help='Max email body chars to send to LLM (default: 4000)')
    parser.add_argument('--llm-output-tokens', type=int, default=300,
                      help='Expected output tokens per email (default: 300)')
    parser.add_argument('--llm-prompt-overhead', type=int, default=200,
                      help='Prompt overhead tokens per email (default: 200)')
    parser.add_argument('--llm-input-rate', type=float, default=_env_float('LLM_INPUT_COST_PER_M_TOKENS'),
                      help='Input cost per 1M tokens (default: env LLM_INPUT_COST_PER_M_TOKENS)')
    parser.add_argument('--llm-output-rate', type=float, default=_env_float('LLM_OUTPUT_COST_PER_M_TOKENS'),
                      help='Output cost per 1M tokens (default: env LLM_OUTPUT_COST_PER_M_TOKENS)')
    parser.add_argument('--llm-dry-run', action='store_true',
                      help='Estimate LLM cost and exit without calling the API')
    parser.add_argument('--llm-approve', action='store_true',
                      help='Skip confirmation prompt for LLM extraction')
    parser.add_argument('--openai-models', action='store_true',
                      help='List available OpenAI models and optionally select one')
    parser.add_argument('--openai-models-prefix', type=str, default=None,
                      help='Filter OpenAI model list by prefix (e.g., gpt-)')
    parser.add_argument('--relax-query', action='store_true',
                      help='Relax Gmail query to date range only (recommended with --llm-filter)')
    args = parser.parse_args()

    if args.openai_models:
        from llm.models import choose_model_interactive, list_openai_models

        api_key = _get_llm_api_key()
        if api_key is None:
            print("OPENAI_API_KEY is not set. Cannot list models.")
            return
        try:
            models = list_openai_models(api_key)
        except RuntimeError as exc:
            print(str(exc))
            return

        if args.openai_models_prefix:
            models = [model for model in models if model.startswith(args.openai_models_prefix)]

        if not models:
            print("No models found for the requested filter.")
            return

        selected = choose_model_interactive(models, args.llm_model)
        if selected:
            args.llm_model = selected

        if not (args.use_llm or args.llm_filter):
            return
    
    storage = EmailStorage()
    latest_file = None
    
    # Handle fetch vs process modes
    if args.fetch_only and args.process_only:
        print("Error: Cannot specify both --fetch-only and --process-only")
        return
        
    # Fetch mode
    if not args.process_only:
        start_date = _parse_start_date(args.year, args.start_date)
        if start_date is None:
            print("Error: Invalid --start-date. Use MM-DD (e.g., 01-15).")
            return

        print(f"Loading emails for {args.year} (looking forward {args.days} days from {start_date.date()})...")
        
        if args.use_sample:
            # Load sample data
            sample_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'sample')
            if not os.path.exists(sample_dir):
                print(f"Error: Sample directory not found at {sample_dir}")
                return
                
            emails = []
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
            query_mode = "relaxed" if args.relax_query or args.llm_filter else "strict"
            emails = fetch_flight_emails(args.year, args.days, start_date=start_date, query_mode=query_mode)
        
        # Save fetched emails
        if emails:
            saved_path = storage.save_emails(emails, args.year)
            print(f"Saved {len(emails)} emails to {saved_path}")
            latest_file = saved_path
    
    # Process mode
    if not args.fetch_only:
        from process_emails import process_stored_emails, LlmSettings
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
        elif latest_file is None:
            # Fallback to most recent stored file if nothing was just fetched.
            email_files = storage.get_email_files(args.year)
            if email_files:
                latest_file = sorted(email_files)[-1]
        
    llm_settings = None
    if args.use_llm or args.llm_filter:
        llm_settings = LlmSettings(
            model=args.llm_model,
            max_body_chars=args.llm_max_body_chars,
            input_cost_per_million=args.llm_input_rate,
            output_cost_per_million=args.llm_output_rate,
            expected_output_tokens=args.llm_output_tokens,
            prompt_overhead_tokens=args.llm_prompt_overhead,
            dry_run=args.llm_dry_run,
            auto_approve=args.llm_approve,
            api_key=_get_llm_api_key(),
            use_extraction=args.use_llm,
            classify_itinerary=args.llm_filter,
            classify_threshold=args.llm_filter_threshold,
            classify_max_body_chars=args.llm_filter_max_body_chars or args.llm_max_body_chars,
            classify_output_tokens=args.llm_filter_output_tokens,
        )

        flights = process_stored_emails(args.year, output_file, latest_file, llm_settings=llm_settings)
        
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
