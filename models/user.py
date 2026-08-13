import uuid

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nickname = Column(String, nullable=False)
    region = Column(String, nullable=True)
    status_level = Column(Integer, nullable=True)
    user_type = Column(String, nullable=True)  # "고립형" | "은둔형" | "복합형"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
