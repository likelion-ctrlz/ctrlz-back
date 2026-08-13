import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from database import Base


class TokenWallet(Base):
    __tablename__ = "token_wallets"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), primary_key=True)
    token_balance = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TokenTransaction(Base):
    __tablename__ = "token_transactions"

    tx_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    amount = Column(Integer, nullable=False)  # 양수=적립, 음수=사용
    reason = Column(String, nullable=False)  # "mission_complete" | "hobby_apply" 등
    ref_id = Column(UUID(as_uuid=True), nullable=True)  # completion_id or participation_id
    created_at = Column(DateTime(timezone=True), server_default=func.now())
