# Summer Training Request Bot

A Telegram bot that auto-fills the university summer training request form (PDF) with your saved profile. Register once, then generate a letter for any company with a single message.

## Features

- Register your profile once (name, university ID, department, remaining hours)
- Generate a filled PDF for any company in seconds
- All data stored in a MySQL database
- Fully Dockerized — run locally or deploy to any server
- Arabic text rendering with correct RTL direction

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/register` | Register or update your profile |
| `/profile` | View your saved profile |
| `/request` | Generate a new training letter |
| `/history` | View your last 5 requests |
| `/help` | Show all commands |
| `./` | Shortcut — show all commands |
| `./help` | Shortcut — show detailed help |

## Project Structure

```
training-form/
├── bot/
│   ├── handlers/       # Telegram command & conversation handlers
│   ├── database/       # SQLAlchemy models and session
│   ├── pdf/            # PDF filling engine + form assets
│   └── main.py         # Bot entry point
├── data/               # Runtime: generated PDFs (volume-mounted)
├── tests/
│   └── test_pdf.py     # Visual PDF calibration test
├── .env                # Secrets (never commit)
├── .env.example        # Template for .env
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url>
cd training-form
cp .env.example .env
# Edit .env with your bot token, DB credentials
```

### 2. Test the PDF filler first

Before running the bot, verify the PDF fields land in the right positions:

```bash
pip install -r requirements.txt
python -m tests.test_pdf
```

This opens a filled test PDF. If any field is misaligned, tweak the coordinates in `bot/pdf/filler.py` → `FIELDS` dict.

### 3. Run with Docker

```bash
docker compose up --build
```

That's it. The bot connects to your MySQL server, creates the tables if needed, and starts polling.

### 4. Deploy to server

Copy the project to your server and run the same command:

```bash
scp -r . user@your-server:/opt/training-form
ssh user@your-server "cd /opt/training-form && docker compose up -d --build"
```

## PDF Coordinate Calibration

The source PDF has no form fields. Text is overlaid at hardcoded coordinates defined in `bot/pdf/filler.py`:

```python
FIELDS = {
    "full_name":       {"x": 477, "y": 671, ...},
    "university_id":   {"x": 213, "y": 671, ...},
    ...
}
```

If fields appear in wrong positions, run `python -m tests.test_pdf`, inspect the output, and adjust `x`/`y` values until correct.

## Database

Tables are auto-created on first run via SQLAlchemy `create_all`.

| Table | Purpose |
|-------|---------|
| `users` | User profiles (telegram_id, name, university info) |
| `training_requests` | Request history per user |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `ADMIN_TELEGRAM_USERNAME` | Your username shown in /help |
| `DB_HOST` | MySQL host |
| `DB_PORT` | MySQL port (default 3306) |
| `DB_NAME` | Database name |
| `DB_USER` | Database user |
| `DB_PASS` | Database password |
| `GENERATED_PDF_DIR` | Where to save generated PDFs |
| `AWS_*` | Phase 3 — S3 storage (optional) |

## Roadmap

- **Phase 1** ✅ — PDF filling engine with Arabic RTL support
- **Phase 2** ✅ — Telegram bot with registration, requests, history, Docker
- **Phase 3** — AWS S3 storage + shareable download links
