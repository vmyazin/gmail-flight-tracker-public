"""
Utilities for estimating LLM token usage and cost, plus confirmation prompts.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import sys
from typing import Dict, Iterable, Optional


DEFAULT_CHARS_PER_TOKEN = 4
DEFAULT_OUTPUT_TOKENS = 300
DEFAULT_PROMPT_OVERHEAD_TOKENS = 200


@dataclass
class LlmCostEstimate:
    email_count: int
    total_input_tokens: int
    total_output_tokens: int
    input_cost: Optional[float]
    output_cost: Optional[float]
    total_cost: Optional[float]
    avg_input_tokens: float
    avg_output_tokens: float
    avg_cost: Optional[float]
    tokenizer: str
    max_body_chars: Optional[int]


@dataclass
class LlmPricing:
    input_cost_per_million: Optional[float]
    output_cost_per_million: Optional[float]


@dataclass
class LlmEstimateConfig:
    model: str
    max_body_chars: Optional[int]
    expected_output_tokens: int = DEFAULT_OUTPUT_TOKENS
    prompt_overhead_tokens: int = DEFAULT_PROMPT_OVERHEAD_TOKENS
    pricing: Optional[LlmPricing] = None


def _get_tokenizer(model: str):
    try:
        import tiktoken
    except Exception:
        return None

    try:
        return tiktoken.encoding_for_model(model)
    except Exception:
        try:
            return tiktoken.get_encoding("cl100k_base")
        except Exception:
            return None


def _estimate_tokens_for_text(text: str, model: str) -> tuple[int, str]:
    tokenizer = _get_tokenizer(model)
    if tokenizer is None:
        tokens = int(math.ceil(len(text) / DEFAULT_CHARS_PER_TOKEN)) if text else 0
        return tokens, f"approx:{DEFAULT_CHARS_PER_TOKEN}chars"

    return len(tokenizer.encode(text)), f"tiktoken:{tokenizer.name}"


def _build_email_prompt(email: Dict, max_body_chars: Optional[int]) -> str:
    subject = email.get("subject", "")
    from_addr = email.get("from", "")
    date = email.get("date", "")
    body = email.get("body", "") or ""

    if max_body_chars is not None and max_body_chars > 0:
        body = body[:max_body_chars]

    return (
        "You are given an email. Extract flight details if present.\n\n"
        f"Subject: {subject}\n"
        f"From: {from_addr}\n"
        f"Date: {date}\n"
        "Body:\n"
        f"{body}\n"
    )


def estimate_llm_cost(
    emails: Iterable[Dict],
    config: LlmEstimateConfig,
) -> LlmCostEstimate:
    total_input_tokens = 0
    tokenizer_name = "approx"
    email_count = 0

    for email in emails:
        email_count += 1
        prompt_text = _build_email_prompt(email, config.max_body_chars)
        tokens, tokenizer_name = _estimate_tokens_for_text(prompt_text, config.model)
        total_input_tokens += tokens + max(config.prompt_overhead_tokens, 0)

    total_output_tokens = max(config.expected_output_tokens, 0) * email_count

    input_cost = None
    output_cost = None
    total_cost = None
    avg_cost = None

    if config.pricing and config.pricing.input_cost_per_million is not None and config.pricing.output_cost_per_million is not None:
        input_cost = (total_input_tokens / 1_000_000.0) * config.pricing.input_cost_per_million
        output_cost = (total_output_tokens / 1_000_000.0) * config.pricing.output_cost_per_million
        total_cost = input_cost + output_cost
        avg_cost = total_cost / email_count if email_count else 0.0

    avg_input_tokens = (total_input_tokens / email_count) if email_count else 0.0
    avg_output_tokens = (total_output_tokens / email_count) if email_count else 0.0

    return LlmCostEstimate(
        email_count=email_count,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=total_cost,
        avg_input_tokens=avg_input_tokens,
        avg_output_tokens=avg_output_tokens,
        avg_cost=avg_cost,
        tokenizer=tokenizer_name,
        max_body_chars=config.max_body_chars,
    )


def format_cost(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"${value:,.4f}" if value >= 0 else "n/a"


def print_llm_cost_estimate(
    estimate: LlmCostEstimate,
    model: str,
    pricing: Optional[LlmPricing],
    label: Optional[str] = None,
) -> None:
    title = "LLM Cost Estimate"
    if label:
        title = f"{title} ({label})"
    print(f"\n{title}")
    print("-" * len(title))
    print(f"Model: {model}")
    print(f"Emails: {estimate.email_count}")
    print(f"Tokenizer: {estimate.tokenizer}")
    if estimate.max_body_chars is not None:
        print(f"Body chars cap: {estimate.max_body_chars}")

    print(f"Input tokens (total): {estimate.total_input_tokens:,}")
    print(f"Output tokens (total): {estimate.total_output_tokens:,}")
    print(f"Input tokens (avg): {estimate.avg_input_tokens:,.1f}")
    print(f"Output tokens (avg): {estimate.avg_output_tokens:,.1f}")

    if pricing and pricing.input_cost_per_million is not None and pricing.output_cost_per_million is not None:
        print(f"Input cost (total): {format_cost(estimate.input_cost)}")
        print(f"Output cost (total): {format_cost(estimate.output_cost)}")
        print(f"Total cost: {format_cost(estimate.total_cost)}")
        print(f"Avg cost/email: {format_cost(estimate.avg_cost)}")
    else:
        print("Pricing: n/a (set input/output rates to estimate cost)")


def confirm_llm_run(dry_run: bool, auto_approve: bool, action: str = "extraction") -> bool:
    if dry_run:
        print("\nDry run enabled. No LLM calls were made.")
        return False

    if auto_approve:
        return True

    if not sys.stdin.isatty():
        print("\nNo TTY available for confirmation. Re-run with --llm-approve to proceed.")
        return False

    response = input(f"\nProceed with LLM {action}? [y/N]: ").strip().lower()
    return response in {"y", "yes"}
