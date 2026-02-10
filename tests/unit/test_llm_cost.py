import math

from utils import llm_cost


def test_estimate_tokens_fallback(monkeypatch):
    monkeypatch.setattr(llm_cost, "_get_tokenizer", lambda model: None)

    tokens, tokenizer = llm_cost._estimate_tokens_for_text("abcd", "gpt-5-mini")
    assert tokens == 1
    assert tokenizer.startswith("approx")

    tokens, _ = llm_cost._estimate_tokens_for_text("abcde", "gpt-5-mini")
    assert tokens == 2


def test_estimate_llm_cost(monkeypatch):
    monkeypatch.setattr(llm_cost, "_get_tokenizer", lambda model: None)

    emails = [
        {"subject": "Test", "from": "x@example.com", "date": "2024-01-01", "body": "abcd"},
        {"subject": "Test2", "from": "y@example.com", "date": "2024-01-02", "body": "abcdefgh"},
    ]

    pricing = llm_cost.LlmPricing(input_cost_per_million=1.0, output_cost_per_million=2.0)
    config = llm_cost.LlmEstimateConfig(
        model="gpt-5-mini",
        max_body_chars=None,
        expected_output_tokens=10,
        prompt_overhead_tokens=5,
        pricing=pricing,
    )

    prompt_1 = llm_cost._build_email_prompt(emails[0], None)
    prompt_2 = llm_cost._build_email_prompt(emails[1], None)

    expected_input_tokens = (
        math.ceil(len(prompt_1) / llm_cost.DEFAULT_CHARS_PER_TOKEN)
        + math.ceil(len(prompt_2) / llm_cost.DEFAULT_CHARS_PER_TOKEN)
        + (config.prompt_overhead_tokens * 2)
    )

    estimate = llm_cost.estimate_llm_cost(emails, config)

    assert estimate.email_count == 2
    assert estimate.total_input_tokens == expected_input_tokens
    assert estimate.total_output_tokens == 20
    assert estimate.total_cost is not None
    assert estimate.avg_cost is not None
