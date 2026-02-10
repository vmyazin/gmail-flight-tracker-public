import json
import os
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.email_fetcher import EmailFetcher

def test_with_file(filename: str):
    """Test our filter with an existing email JSON file."""
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    fetcher = EmailFetcher()
    filtered = fetcher.fetch_and_filter_emails(data['emails'])
    
    return filtered

if __name__ == "__main__":
    # Test with our most recent email file
    test_file = "data/raw_emails/emails_2024_20241226_023049.json"
    filtered_emails = test_with_file(test_file) 