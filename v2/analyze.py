"""
# v2/analyze.py
# Simplified flight listing and CSV export for Gmail Flight Tracker v2
"""

import os
import json
import csv
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class FlightDataAnalyzer:
    def __init__(self, data_file: str):
        self.data_file = data_file
        self.data = self._load_data()
        self.df = self._create_dataframe()

    def _load_data(self) -> Dict[str, Any]:
        """Load flight data from JSON file."""
        with open(self.data_file, 'r') as f:
            return json.load(f)

    def _create_dataframe(self) -> pd.DataFrame:
        """Convert flight data to pandas DataFrame for analysis."""
        return pd.DataFrame(self.data['flights'])

    def generate_report(self, output_dir: str = "reports"):
        """Generate simple flight listing report."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create report
        report = [
            "# Flight Listing Report",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Flights",
            ""
        ]

        # Add each flight as a list item
        for flight in self.data['flights']:
            flight_info = []
            
            # Flight number and airline
            if 'flightNumber' in flight:
                flight_info.append(f"Flight: {flight['flightNumber']}")
            if 'airline' in flight:
                flight_info.append(f"Airline: {flight['airline']}")
                
            # Confirmation code
            if 'confirmationCode' in flight:
                flight_info.append(f"Confirmation: {flight['confirmationCode']}")
            
            # Date
            if 'date' in flight:
                try:
                    date = datetime.fromtimestamp(int(flight['date'])/1000).strftime('%Y-%m-%d %H:%M')
                    flight_info.append(f"Date: {date}")
                except (ValueError, TypeError):
                    pass
            
            # Add to report with bullet point
            report.append(f"- {' | '.join(flight_info)}")
        
        # Save report
        report_file = os.path.join(output_dir, f"flight_listing_{timestamp}.md")
        with open(report_file, 'w') as f:
            f.write('\n'.join(report))
        
        # Generate CSV
        self._export_csv(output_dir, timestamp)
        
        print(f"\nReport generated: {report_file}")
        return report_file

    def _export_csv(self, output_dir: str, timestamp: str):
        """Export flights to CSV in the specified format."""
        csv_file = os.path.join(output_dir, f"flights_{timestamp}.csv")
        
        # CSV headers
        headers = [
            'flight_number',
            'airline',
            'departure_airport',
            'arrival_airport',
            'departure_datetime',
            'arrival_datetime',
            'duration'
        ]
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            
            for flight in self.data['flights']:
                # Prepare row data
                row = {
                    'flight_number': flight.get('flightNumber', ''),
                    'airline': flight.get('airline', ''),
                    'departure_airport': flight.get('departure_airport', ''),
                    'arrival_airport': flight.get('arrival_airport', ''),
                    'departure_datetime': '',
                    'arrival_datetime': '',
                    'duration': ''
                }
                
                # Convert timestamp to datetime if available
                if 'date' in flight:
                    try:
                        departure_datetime = datetime.fromtimestamp(
                            int(flight['date'])/1000
                        ).strftime('%Y-%m-%d %H:%M')
                        row['departure_datetime'] = departure_datetime
                    except (ValueError, TypeError):
                        pass
                
                writer.writerow(row)
        
        print(f"CSV exported: {csv_file}")

def main():
    # Get root directory
    root_dir = Path(__file__).parent.parent
    
    # Find most recent flight data file
    data_dir = root_dir / "data" / "processed"
    flight_files = list(data_dir.glob("flights_*.json"))
    if not flight_files:
        print("No flight data files found!")
        return
    
    latest_file = max(flight_files, key=lambda x: x.stat().st_mtime)
    print(f"Analyzing: {latest_file}")
    
    # Create analyzer and generate report
    analyzer = FlightDataAnalyzer(str(latest_file))
    report_file = analyzer.generate_report(str(root_dir / "reports"))
    
    print("\nAnalysis complete! You can find the report and CSV in the reports directory.")

if __name__ == "__main__":
    main() 