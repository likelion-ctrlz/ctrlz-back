import uuid

from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Mission(Base):
    __tablename__ = "missions"

    mission_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    difficulty = Column(Integer, nullable=False, default=1)  # 1(쉬움) ~ 5(어려움)
    category = Column(String, nullable=True)  # "외출" | "관계" | "자기관리" 등
    target_level = Column(ARRAY(Integer), nullable=True)
    target_type = Column(ARRAY(String), nullable=True)
    verification_type = Column(String, nullable=False, default="photo")  # "photo" | "text" | "none"
    token_reward = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MissionCompletion(Base):
    __tablename__ = "mission_completions"

    completion_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    mission_id = Column(UUID(as_uuid=True), ForeignKey("missions.mission_id"), nullable=False)
    photo_url = Column(String, nullable=True)
    photo_gps_lat = Column(Float, nullable=True)
    photo_gps_lng = Column(Float, nullable=True)
    photo_taken_at = Column(DateTime(timezone=True), nullable=True)
    ai_verdict = Column(Boolean, nullable=True)
    ai_feedback = Column(Text, nullable=True)
    token_earned = Column(Integer, nullable=False, default=0)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False, default="pending")
    # "pending" | "ai_processing" | "approved" | "rejected"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    mission = relationship("Mission")
