from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    kakao_id = Column(String, unique=True, nullable=True, index=True)
    google_id = Column(String, unique=True, nullable=True, index=True)
    email = Column(String, unique=True, nullable=True)
    nickname = Column(String, nullable=True)
    profile_image = Column(String, nullable=True)
    user_type = Column(String, nullable=True)  # 예: "은둔형"
    token_balance = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
