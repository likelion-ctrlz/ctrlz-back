import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from database import Base


class DailyReport(Base):
    __tablename__ = "daily_reports"

    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    date = Column(Date, nullable=False)
    mission_summary = Column(JSONB, nullable=True)
    # {"completed": 2, "tokens_earned": 30, "missions": ["공원 다녀오기", ...]}
    ai_report_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "date"),)
