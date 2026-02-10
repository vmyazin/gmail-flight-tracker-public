"""
LLM-based flight information extraction.
"""

from __future__ import annotations

from typing import Dict, Optional


def _build_prompt(email: Dict, max_body_chars: Optional[int]) -> str:
    subject = email.get("subject", "")
    from_addr = email.get("from", "")
    date = email.get("date", "")
    body = email.get("body", "") or ""

    if max_body_chars is not None and max_body_chars > 0:
        body = body[:max_body_chars]

    return (
        "Extract flight details from the email. "
        "If a field is not present, return null. "
        "Prefer IATA airport codes and ISO 8601 date/time if possible.\n\n"
        f"Subject: {subject}\n"
        f"From: {from_addr}\n"
        f"Date: {date}\n"
        "Body:\n"
        f"{body}\n"
    )


def _build_classification_prompt(email: Dict, max_body_chars: Optional[int]) -> str:
    subject = email.get("subject", "")
    from_addr = email.get("from", "")
    date = email.get("date", "")
    body = email.get("body", "") or ""

    if max_body_chars is not None and max_body_chars > 0:
        body = body[:max_body_chars]

    return (
        "Decide if this email is a travel itinerary or contains actionable travel reservation info. "
        "Return true for flights, boarding passes, check-in notices, ticketing, or reservations with "
        "dates, cities, airports, or booking codes. Return false for promos, surveys, blogs, loyalty "
        "marketing, or unrelated travel content.\n\n"
        f"Subject: {subject}\n"
        f"From: {from_addr}\n"
        f"Date: {date}\n"
        "Body:\n"
        f"{body}\n"
    )


def classify_itinerary_email_llm(
    email: Dict,
    model: str,
    max_body_chars: Optional[int] = None,
    api_key: Optional[str] = None,
) -> Optional[Dict]:
    try:
        from openai import BadRequestError, OpenAI
        from pydantic import BaseModel, Field
    except Exception as exc:
        raise RuntimeError("openai and pydantic packages are required for LLM classification") from exc

    class LlmItineraryDecision(BaseModel):
        is_itinerary: bool = Field(description="True if email is a travel itinerary or reservation")
        confidence: Optional[float] = Field(default=None, ge=0, le=1, description="0-1 confidence")
        reason: Optional[str] = Field(default=None, description="Short reason for the decision")

    client = OpenAI(api_key=api_key)
    prompt = _build_classification_prompt(email, max_body_chars)

    try:
        response = client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": "You classify travel itinerary emails."},
                {"role": "user", "content": prompt},
            ],
            text_format=LlmItineraryDecision,
            temperature=0,
        )
    except BadRequestError as exc:
        message = str(exc)
        if "temperature" in message and "not supported" in message:
            response = client.responses.parse(
                model=model,
                input=[
                    {"role": "system", "content": "You classify travel itinerary emails."},
                    {"role": "user", "content": prompt},
                ],
                text_format=LlmItineraryDecision,
            )
        else:
            raise

    parsed = response.output_parsed
    if not parsed:
        return None

    result = parsed.model_dump()
    # Normalize empty strings to None
    for key, value in list(result.items()):
        if isinstance(value, str) and not value.strip():
            result[key] = None

    return result


def extract_flight_info_llm(
    email: Dict,
    model: str,
    max_body_chars: Optional[int] = None,
    api_key: Optional[str] = None,
) -> Optional[Dict]:
    try:
        from openai import BadRequestError, OpenAI
        from pydantic import BaseModel, Field
    except Exception as exc:
        raise RuntimeError("openai and pydantic packages are required for LLM extraction") from exc

    class LlmFlightInfo(BaseModel):
        flight_number: Optional[str] = Field(default=None, description="Airline code + flight number")
        departure_datetime: Optional[str] = Field(default=None, description="Departure date/time if present")
        arrival_datetime: Optional[str] = Field(default=None, description="Arrival date/time if present")
        departure_airport: Optional[str] = Field(default=None, description="IATA departure airport code")
        arrival_airport: Optional[str] = Field(default=None, description="IATA arrival airport code")
        confirmation_code: Optional[str] = Field(default=None, description="Booking/PNR/confirmation code")
        airline: Optional[str] = Field(default=None, description="Airline name if present")
        confidence: Optional[float] = Field(default=None, ge=0, le=1, description="0-1 confidence")

    client = OpenAI(api_key=api_key)
    prompt = _build_prompt(email, max_body_chars)

    try:
        response = client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": "You extract structured flight details from travel emails."},
                {"role": "user", "content": prompt},
            ],
            text_format=LlmFlightInfo,
            temperature=0,
        )
    except BadRequestError as exc:
        message = str(exc)
        if "temperature" in message and "not supported" in message:
            response = client.responses.parse(
                model=model,
                input=[
                    {"role": "system", "content": "You extract structured flight details from travel emails."},
                    {"role": "user", "content": prompt},
                ],
                text_format=LlmFlightInfo,
            )
        else:
            raise

    parsed = response.output_parsed
    if not parsed:
        return None

    result = parsed.model_dump()
    # Normalize empty strings to None
    for key, value in list(result.items()):
        if isinstance(value, str) and not value.strip():
            result[key] = None

    return result
