import uuid

from sqlalchemy import ARRAY, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from database import Base


class Program(Base):
    __tablename__ = "programs"

    program_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    agency_name = Column(String, nullable=True)
    region = Column(String, nullable=True)  # "서울 종로구" 등
    target_type = Column(ARRAY(String), nullable=True)
    target_level = Column(ARRAY(Integer), nullable=True)
    description = Column(Text, nullable=True)
    contact = Column(String, nullable=True)
    apply_url = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


class ProgramReferral(Base):
    __tablename__ = "program_referrals"

    referral_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.program_id"), nullable=False)
    status = Column(String, nullable=False, default="viewed")  # "viewed" | "applied"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
