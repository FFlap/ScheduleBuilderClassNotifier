# "My Schedule Builder" Class Notifier

Checks university schedules and sends a Discord alert when a seat opens. Haven't tested it for other universities 
schedule builders, but it should work if they have the same UI.

## Prerequisites
- Python 3.10+
- Google Chrome and a matching ChromeDriver (may need to install ChromeDriver separately)

## Setup
1. Clone or download this repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and set your webhook URL:
   ```bash
   cp .env.example .env
   # edit .env and set DISCORD_WEBHOOK_URL
   ```
4. Add the course schedule URLs you want to monitor to `scheduleUrls.txt` (one per line). Leave the example entry or replace it with your own.

## Configuration
- `DISCORD_WEBHOOK_URL` (in `.env`): Discord webhook that receives alerts.
- `scheduleUrls.txt`: Plaintext list of schedule pages to check. Lines starting with `#` are ignored.

## Usage
Run the notifier:
```bash
python main.py
```

The script runs headless Chrome, checks each URL, and posts to your Discord webhook when a course shows available seats. It waits a random 5–15 minutes (plus 0–30 seconds) between checks to avoid spam and detection.
