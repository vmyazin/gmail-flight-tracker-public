"""
Helpers for listing and selecting OpenAI models.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence
import sys


ALLOWED_TEXT_MODELS = {
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-4.1-mini",
    "gpt-4o-mini",
}


def _unique_sorted(items: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return sorted(result)


def list_openai_models(
    api_key: Optional[str],
    allowlist: Optional[Sequence[str]] = None,
) -> List[str]:
    try:
        from openai import OpenAI
    except Exception as exc:
        raise RuntimeError("openai package is required to list models") from exc

    client = OpenAI(api_key=api_key)
    response = client.models.list()
    models = []
    for model in getattr(response, "data", []) or []:
        model_id = getattr(model, "id", None)
        if isinstance(model, dict):
            model_id = model.get("id")
        if model_id:
            models.append(model_id)
    filtered = models
    if allowlist is None:
        allowlist = sorted(ALLOWED_TEXT_MODELS)

    if allowlist:
        allowed = set(allowlist)
        filtered = [model for model in models if model in allowed]

    return _unique_sorted(filtered)


def format_model_choices(models: List[str], selected: Optional[str]) -> str:
    lines = []
    width = len(str(len(models)))
    for idx, model in enumerate(models, 1):
        marker = "(*)" if model == selected else "( )"
        lines.append(f"{str(idx).rjust(width)}. {marker} {model}")
    return "\n".join(lines)


def choose_model_interactive(models: List[str], selected: Optional[str]) -> Optional[str]:
    if not models:
        return selected

    print(format_model_choices(models, selected))

    if not sys.stdin.isatty():
        return selected

    choice = input("\nSelect model by number or name (Enter to keep current): ").strip()
    if not choice:
        return selected

    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(models):
            return models[idx - 1]
        print("Invalid selection. Keeping current model.")
        return selected

    if choice in models:
        return choice

    print("Model not found. Keeping current model.")
    return selected
