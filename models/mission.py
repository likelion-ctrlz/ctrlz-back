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
    detail_description = Column(Text, nullable=True)  # 미션 상세 페이지용 긴 설명
    difficulty = Column(Integer, nullable=False, default=1)  # 1(쉬움) ~ 7(어려움)
    category = Column(String, nullable=True)  # "외출" | "관계" | "자기관리" 등
    target_level = Column(ARRAY(Integer), nullable=True)
    target_type = Column(ARRAY(String), nullable=True)
    verification_type = Column(String, nullable=False, default="photo")  # "photo" | "text" | "none"
    conditions = Column(ARRAY(String), nullable=True)  # 인증 조건 체크리스트
    xp_reward = Column(Integer, nullable=False, default=0)  # 완료 시 지급 XP
    token_reward = Column(Integer, nullable=False, default=0)
    bonus_token = Column(Integer, nullable=False, default=0)  # 보너스 토큰 (미션별 임의 설정)
    is_wow = Column(Boolean, nullable=False, default=False)  # 와우포인트 미션 여부 (데모 고정 노출)
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
    xp_earned = Column(Integer, nullable=False, default=0)
    token_earned = Column(Integer, nullable=False, default=0)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False, default="pending")
    # "pending" | "ai_processing" | "approved" | "rejected"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    mission = relationship("Mission")
