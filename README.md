# Summer Training Request Bot

A Telegram bot that auto-fills the university summer training request form (PDF) with your saved profile. Register once, then generate a letter for any company with a single message.

## Features

- Register your profile once (name, university ID, department, remaining hours)
- Generate a filled PDF for any company in seconds
- All data stored in a MySQL database
- Fully Dockerized — run locally or deploy to any server
- Arabic text rendering with correct RTL direction

---

## How to Run

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A `.env` file with your credentials (already set up if you're the owner)

---

### Run locally (first time)

```bash
docker compose up --build
```

This command:
1. Downloads the Python base image
2. Installs all dependencies
3. Downloads the Arabic font
4. Starts the bot

You'll see logs like:
```
training_form_bot  | Database initialised
training_form_bot  | Bot starting...
```

The bot is now live. Open Telegram and message [@training_form_request_bot](https://t.me/training_form_request_bot).

---

### Run locally (after first build)

```bash
docker compose up
```

No `--build` needed unless you changed the code.

---

### Run in background (so it keeps running after you close the terminal)

```bash
docker compose up -d --build
```

The `-d` flag runs it detached (in the background ).

---

### Stop the bot

```bash
docker compose down
```

---

### View live logs

```bash
docker compose logs -f
```

---

### Restart after a code change

```bash
docker compose up --build
```

---

## Deploy to Your Server

Copy the project to the server and run:

```bash
# From your local machine — copy the project
scp -r . user@your-server-ip:/opt/training-form

# SSH into the server
ssh user@your-server-ip

# Go to the project folder and start
cd /opt/training-form
docker compose up -d --build
```

The bot will keep running on the server even after you disconnect.

To check it's running on the server:
```bash
docker compose ps
docker compose logs -f
```

---

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

---

## Project Structure

```
training-form/
├── bot/
│   ├── handlers/       # Telegram command & conversation handlers
│   ├── database/       # SQLAlchemy models and session
│   ├── pdf/            # PDF filling engine + form assets + font
│   └── main.py         # Bot entry point
├── data/               # Runtime: generated PDFs (volume-mounted, not in git)
├── tests/
│   └── test_pdf.py     # Visual PDF calibration test
├── .env                # Your secrets — never commit this
├── .env.example        # Template for .env (safe to commit)
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## PDF Field Calibration

If text appears in the wrong position on the PDF, run this locally:

```bash
pip3 install -r requirements.txt
PYTHONPATH=. python3 -m tests.test_pdf
```

It generates a filled test PDF at `/tmp/test_training_form.pdf` and opens it automatically. Adjust the `x`/`y` coordinates in `bot/pdf/filler.py` → `FIELDS` dict until everything looks right.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `ADMIN_TELEGRAM_USERNAME` | Your username shown in /help |
| `DB_HOST` | MySQL host or IP |
| `DB_PORT` | MySQL port (default `3306`) |
| `DB_NAME` | Database name |
| `DB_USER` | Database user |
| `DB_PASS` | Database password |
| `GENERATED_PDF_DIR` | Path inside container for saved PDFs (default `/app/data/generated`) |
| `AWS_*` | Phase 3 only — S3 storage (leave empty to skip) |

---

## Database

Tables are created automatically on first run. No manual setup needed.

| Table | Purpose |
|-------|---------|
| `users` | User profiles (telegram_id, name, university info) |
| `training_requests` | Request history per user |

---

## Roadmap

- **Phase 1** ✅ — PDF filling engine with Arabic RTL support
- **Phase 2** ✅ — Telegram bot with registration, requests, history, Docker
- **Phase 3** — AWS S3 storage + shareable download links
