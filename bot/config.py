import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_TELEGRAM_USERNAME: str = os.getenv("ADMIN_TELEGRAM_USERNAME", "")

DB_HOST: str = os.environ["DB_HOST"]
DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
DB_NAME: str = os.environ["DB_NAME"]
DB_USER: str = os.environ["DB_USER"]
DB_PASS: str = os.environ["DB_PASS"]

GENERATED_PDF_DIR: str = os.getenv("GENERATED_PDF_DIR", "/app/data/generated")

# Phase 3: S3 (optional — empty means use local disk)
AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_S3_BUCKET: str = os.getenv("AWS_S3_BUCKET", "")
AWS_REGION: str = os.getenv("AWS_REGION", "")

USE_S3: bool = bool(AWS_ACCESS_KEY_ID and AWS_S3_BUCKET)

PDF_FORM_PATH: str  = os.path.join(os.path.dirname(__file__), "pdf", "assets", "form.pdf")
FONT_PATH: str      = os.path.join(os.path.dirname(__file__), "pdf", "assets", "Amiri-Regular.ttf")
FONT_BOLD_PATH: str = os.path.join(os.path.dirname(__file__), "pdf", "assets", "Amiri-Bold.ttf")
