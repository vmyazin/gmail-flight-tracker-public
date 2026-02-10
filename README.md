# Gmail Flight Tracker

A Python tool to automatically extract and aggregate flight information from Gmail, creating a consolidated travel history with minimal manual input.

This repository is a public-friendly export and includes source only. Runtime data, logs, and credentials are created locally and are not versioned.

## Features

- Automatically fetches flight-related emails from Gmail
- Supports multiple email formats (VietJet Air, Trip.com, Booking.com)
- Extracts key flight information (flight numbers, airports, dates, times, airlines, duration)
- Two-step flow: fetch raw emails, then process stored emails
- Deduplicates flight entries
- Outputs clean, formatted results

## Setup

1. Clone and enter the repo:
```bash
git clone https://github.com/yourusername/gmail-flight-tracker.git
cd gmail-flight-tracker
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up Google Cloud Project and Gmail API:

   a. Go to the Google Cloud Console

   b. Create a new project or select an existing one

   c. Enable the Gmail API

   d. Create credentials (OAuth client ID, Desktop app)

   e. Place the downloaded credentials file in `credentials/`

5. Configure accounts:

   Copy the template and update the credentials path:
```bash
mkdir -p config
cp config/accounts_template.json config/accounts.json
```

Edit `config/accounts.json` to match the credentials file name you saved.

## Usage

### 1. Fetch Emails
```bash
python src/main.py --year 2024 --days 365 --fetch-only
```

### 2. Process Stored Emails
```bash
python src/main.py --year 2024 --process-only
```

### Combined Operation
```bash
python src/main.py --year 2024 --days 365
```

### Command Line Options

- `--year`: Year to search for flights (default: current year)
- `--days`: Number of days to look forward from start of year (default: 365)
- `--use-sample`: Use sample data instead of Gmail API (place JSON files in `data/sample`)
- `--fetch-only`: Only fetch and store emails, do not process them
- `--process-only`: Only process stored emails, do not fetch new ones

## Notes

- Runtime directories are created as needed: `credentials/`, `data/`, `logs/`, `reports/`.
- If you want to use sample data, place your own JSON emails in `data/sample`.
