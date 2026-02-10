import json
import os
import sys
from pathlib import Path
import pytest

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.email_fetcher import EmailFetcher

SAMPLE_EMAIL_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "raw_emails"
    / "emails_2024_20241226_023049.json"
)

@pytest.fixture(scope="session")
def sample_emails():
    if not SAMPLE_EMAIL_FILE.exists():
        pytest.skip(f"Sample email file not found: {SAMPLE_EMAIL_FILE}")

    with SAMPLE_EMAIL_FILE.open('r', encoding='utf-8') as f:
        data = json.load(f)

    assert "emails" in data
    return data["emails"]

def test_with_file(sample_emails):
    """Test our filter with a sample email JSON file."""
    fetcher = EmailFetcher()
    filtered = fetcher.fetch_and_filter_emails(sample_emails)

    assert isinstance(filtered, list)
    if filtered:
        for email in filtered:
            assert "booking_details" in email

if __name__ == "__main__":
    # Test with our most recent email file
    test_file = str(SAMPLE_EMAIL_FILE)
    with open(test_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    filtered_emails = EmailFetcher().fetch_and_filter_emails(data['emails'])
