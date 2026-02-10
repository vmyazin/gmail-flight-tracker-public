"""
# src/process_emails.py
# Script for processing stored emails and extracting flight information
"""

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
import os
from typing import List, Dict, Optional

from dotenv import load_dotenv
from storage.email_storage import EmailStorage
from parsers.flight_parser import parse_flight_email, format_flight_details
from main import deduplicate_flights
from utils.llm_cost import (
    LlmEstimateConfig,
    LlmPricing,
    confirm_llm_run,
    estimate_llm_cost,
    print_llm_cost_estimate,
)
from llm.extractor import classify_itinerary_email_llm, extract_flight_info_llm


@dataclass
class LlmSettings:
    model: str
    max_body_chars: Optional[int]
    input_cost_per_million: Optional[float]
    output_cost_per_million: Optional[float]
    expected_output_tokens: int
    prompt_overhead_tokens: int
    dry_run: bool
    auto_approve: bool
    api_key: Optional[str]
    use_extraction: bool = True
    classify_itinerary: bool = False
    classify_threshold: float = 0.6
    classify_max_body_chars: Optional[int] = None
    classify_output_tokens: int = 60

def process_stored_emails(
    year: int = None,
    output_file: str = None,
    specific_file: str = None,
    llm_settings: Optional[LlmSettings] = None,
) -> List[Dict]:
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

    if llm_settings is not None and (llm_settings.use_extraction or llm_settings.classify_itinerary):
        pricing = LlmPricing(
            input_cost_per_million=llm_settings.input_cost_per_million,
            output_cost_per_million=llm_settings.output_cost_per_million,
        )
        if llm_settings.classify_itinerary:
            classify_config = LlmEstimateConfig(
                model=llm_settings.model,
                max_body_chars=llm_settings.classify_max_body_chars,
                expected_output_tokens=llm_settings.classify_output_tokens,
                prompt_overhead_tokens=llm_settings.prompt_overhead_tokens,
                pricing=pricing,
            )
            classify_estimate = estimate_llm_cost(emails, classify_config)
            print_llm_cost_estimate(classify_estimate, llm_settings.model, pricing, "Classification")

        if llm_settings.use_extraction:
            estimate_config = LlmEstimateConfig(
                model=llm_settings.model,
                max_body_chars=llm_settings.max_body_chars,
                expected_output_tokens=llm_settings.expected_output_tokens,
                prompt_overhead_tokens=llm_settings.prompt_overhead_tokens,
                pricing=pricing,
            )
            estimate = estimate_llm_cost(emails, estimate_config)
            print_llm_cost_estimate(estimate, llm_settings.model, pricing, "Extraction")

        if pricing.input_cost_per_million is None or pricing.output_cost_per_million is None:
            print("\nLLM pricing rates are required to proceed.")
            print("Set LLM_INPUT_COST_PER_M_TOKENS and LLM_OUTPUT_COST_PER_M_TOKENS,")
            print("or pass --llm-input-rate/--llm-output-rate.")
            return []

        if llm_settings.use_extraction and llm_settings.classify_itinerary:
            llm_action = "classification and extraction"
        elif llm_settings.use_extraction:
            llm_action = "extraction"
        else:
            llm_action = "classification"

        confirmed = confirm_llm_run(llm_settings.dry_run, llm_settings.auto_approve, llm_action)
        if not confirmed:
            if llm_settings.dry_run:
                return []
            print("\nLLM processing cancelled.")
            return []

        if llm_settings.api_key is None:
            print("\nOPENAI_API_KEY is not set. Cannot run LLM processing.")
            return []

        try:
            import openai  # noqa: F401
            import pydantic  # noqa: F401
        except Exception:
            print("\nMissing LLM dependencies. Install with: pip install openai pydantic")
            return []
    flight_info_list = []
    
    for email in emails:
        print(f"\nProcessing email: {email.get('subject')}")
        if llm_settings is not None and llm_settings.classify_itinerary:
            try:
                decision = classify_itinerary_email_llm(
                    email,
                    model=llm_settings.model,
                    max_body_chars=llm_settings.classify_max_body_chars,
                    api_key=llm_settings.api_key,
                )
            except RuntimeError as exc:
                print(f"LLM classification failed: {exc}")
                return []

            if decision is not None:
                confidence = decision.get("confidence") or 0.0
                if not decision.get("is_itinerary", False) and confidence >= llm_settings.classify_threshold:
                    reason = decision.get("reason")
                    if reason:
                        print(f"Skipped by LLM filter: {reason}")
                    else:
                        print("Skipped by LLM filter")
                    continue

        flight_info = parse_flight_email(email)
        if flight_info:
            flight_dict = flight_info.to_dict()
        elif llm_settings is not None and llm_settings.use_extraction:
            try:
                flight_dict = extract_flight_info_llm(
                    email,
                    model=llm_settings.model,
                    max_body_chars=llm_settings.max_body_chars,
                    api_key=llm_settings.api_key,
                )
            except RuntimeError as exc:
                print(f"LLM extraction failed: {exc}")
                return []
        else:
            flight_dict = None

        if flight_dict:
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

def _env_float(name: str) -> Optional[float]:
    value = os.getenv(name)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _get_llm_api_key() -> Optional[str]:
    return os.getenv("OPENAI_API_KEY")


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description='Process stored emails to extract flight information')
    parser.add_argument('--year', type=int, help='Year to process emails for (default: all years)')
    parser.add_argument('--output', type=str, help='Path to save results to (default: data/processed/flights_YYYY.json)')
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
    args = parser.parse_args()
    
    # If no output file specified, use default
    if not args.output and args.year:
        args.output = f"data/processed/flights_{args.year}.json"
    elif not args.output:
        args.output = "data/processed/flights_all.json"
    
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

    process_stored_emails(args.year, args.output, llm_settings=llm_settings)

if __name__ == '__main__':
    main() 
