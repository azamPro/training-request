from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text,
    DateTime, ForeignKey, func
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    telegram_username = Column(String(64), nullable=True)
    full_name = Column(String(150), nullable=False)
    university_id = Column(String(20), nullable=False)
    department = Column(String(100), nullable=False)
    remaining_hours = Column(String(10), nullable=False)
    signature_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    requests = relationship("TrainingRequest", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User telegram_id={self.telegram_id} name={self.full_name}>"


class TrainingRequest(Base):
    __tablename__ = "training_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_name = Column(String(200), nullable=False)
    company_description = Column(String(500), nullable=True)
    pdf_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="requests")

    def __repr__(self) -> str:
        return f"<TrainingRequest id={self.id} company={self.company_name}>"
