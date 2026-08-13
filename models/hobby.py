import uuid

from sqlalchemy import ARRAY, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from database import Base


class HobbyActivity(Base):
    __tablename__ = "hobby_activities"

    hobby_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)  # "예술" | "운동" | "원예" 등
    token_cost = Column(Integer, nullable=False, default=0)
    recommended_level = Column(ARRAY(Integer), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


class HobbyParticipation(Base):
    __tablename__ = "hobby_participations"

    participation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    hobby_id = Column(UUID(as_uuid=True), ForeignKey("hobby_activities.hobby_id"), nullable=False)
    token_used = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="applied")
    # "applied" | "confirmed" | "cancelled"
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
