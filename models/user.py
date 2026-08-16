import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nickname = Column(String, nullable=False)
    region = Column(String, nullable=True)
    is_demo = Column(Boolean, nullable=False, default=False)  # 데모 모드 여부

    # 자가진단 결과 (자가진단 완료 전 NULL)
    assessment_level = Column(Integer, nullable=True)  # 1~4 (1=가장 심각)
    assessment_type = Column(String, nullable=True)  # 관찰군|고립형|은둔형|복합형
    assessment_score = Column(Integer, nullable=True)  # 홈 표시용 0~10점
    assessed_at = Column(DateTime(timezone=True), nullable=True)

    # 캐릭터 (게임화)
    character_level = Column(Integer, nullable=False, default=1)  # 1~4
    character_xp = Column(Integer, nullable=False, default=0)  # 누적 XP

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
