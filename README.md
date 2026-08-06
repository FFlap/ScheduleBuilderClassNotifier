# "My Schedule Builder" Class Notifier

Checks university schedules and sends an ntfy alert when a seat opens. Haven't tested it for other universities
schedule builders, but it should work if they have the same UI.

## Prerequisites
- Python 3.10+

## Setup
1. Clone or download this repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env`, set your ntfy topic URL, and subscribe to the
   same topic in the ntfy app:
   ```bash
   cp .env.example .env
   # edit .env and set NTFY_TOPIC_URL
   ```
4. Add the course schedule URLs you want to monitor to `scheduleUrls.txt` (one per line). Leave the example entry or replace it with your own.

## Configuration
- `NTFY_TOPIC_URL` (in `.env`): Full ntfy publish URL, such as `https://ntfy.sh/your-private-topic`.
- `scheduleUrls.txt`: Plaintext list of schedule pages to check. Lines starting with `#` are ignored.

## Usage
Run the notifier:
```bash
python main.py
```

The script queries My Schedule Builder's class-data endpoint, checks each URL, posts to the ntfy topic when a course shows available seats, and then exits. Schedule it with cron or another job runner to check repeatedly.
