import logging
import time
from contextlib import contextmanager
from typing import Generator
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from bot.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS
from bot.database.models import Base, BotEvent

logger = logging.getLogger(__name__)

# quote_plus encodes special URL chars (>, ?, &, etc.) in user/password
DATABASE_URL = (
    f"mysql+pymysql://{quote_plus(DB_USER)}:{quote_plus(DB_PASS)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # detect stale connections
    pool_recycle=3600,        # recycle connections every hour
    pool_size=5,
    max_overflow=10,
    echo=False,
)

# expire_on_commit=False keeps attribute values accessible after session closes
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db(retries: int = 10, delay: float = 5.0) -> None:
    """Create tables, retrying until DB is reachable."""
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except Exception as exc:
            logger.warning("DB init attempt %d/%d failed: %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(delay)
    raise RuntimeError(f"Could not connect to database after {retries} attempts")


def log_event(telegram_id: int, event_type: str, payload: str | None = None) -> None:
    """Write a bot_events row. Never raises — failures are silently logged."""
    try:
        with get_db() as db:
            db.add(BotEvent(telegram_id=telegram_id, event_type=event_type, payload=payload))
    except Exception as exc:
        logger.warning("log_event failed (%s): %s", event_type, exc)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
