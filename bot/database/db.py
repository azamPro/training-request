from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from bot.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS
from bot.database.models import Base

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


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


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
