import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from database import Base


class DiaryEntry(Base):
    __tablename__ = "diary_entries"

    entry_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    audio_url = Column(String, nullable=True)  # S3 URL (음성 입력 시)
    text_content = Column(Text, nullable=True)  # 텍스트 입력 or STT 결과
    transcript = Column(Text, nullable=True)  # STT 최종 텍스트
    emotion_summary = Column(JSONB, nullable=True)
    # 예: {"primary": "불안", "secondary": "외로움", "score": {"불안": 0.7, ...}}
    risk_flag = Column(Boolean, nullable=False, default=False)  # 위기 신호 감지 여부
    created_at = Column(DateTime(timezone=True), server_default=func.now())
