"""
# src/storage/email_storage.py
# Module for storing and loading raw email data
"""

import json
import os
from datetime import datetime
from typing import List, Dict
import fnmatch

class EmailStorage:
    def __init__(self, storage_dir: str = "data/raw_emails"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def save_emails(self, emails: List[Dict], year: int) -> str:
        """
        Save raw emails to a JSON file
        
        Args:
            emails: List of email dictionaries
            year: Year the emails were fetched for
            
        Returns:
            Path to the saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"emails_{year}_{timestamp}.json"
        filepath = os.path.join(self.storage_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'fetch_date': datetime.now().isoformat(),
                    'year': year,
                    'email_count': len(emails)
                },
                'emails': emails
            }, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def load_emails(self, year: int = None, specific_file: str = None) -> List[Dict]:
        """
        Load emails from storage.
        
        Args:
            year: Optional year to filter by
            specific_file: Optional specific file to load
        """
        emails = []
        
        try:
            if specific_file and os.path.exists(specific_file):
                # Load single specified file
                with open(specific_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('emails', [])
                    
            # Default email directory
            email_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                    'data', 'raw_emails')
            
            if not os.path.exists(email_dir):
                return []
                
            return emails
            
        except Exception as e:
            print(f"Error loading emails: {str(e)}")
            return []
    
    def get_available_years(self) -> List[int]:
        """Get list of years for which we have stored emails"""
        years = set()
        
        for filename in os.listdir(self.storage_dir):
            if not filename.endswith('.json'):
                continue
                
            filepath = os.path.join(self.storage_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    years.add(data['metadata']['year'])
            except:
                continue
        
        return sorted(list(years)) 
    
    def get_email_files(self, year: int) -> List[str]:
        """Get all email files for a specific year."""
        email_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                'data', 'raw_emails')
        
        if not os.path.exists(email_dir):
            return []
        
        # Look for files matching pattern emails_YEAR_*.json
        pattern = f"emails_{year}_*.json"
        matching_files = []
        
        for filename in os.listdir(email_dir):
            if fnmatch.fnmatch(filename, pattern):
                matching_files.append(os.path.join(email_dir, filename))
                
        return matching_files 