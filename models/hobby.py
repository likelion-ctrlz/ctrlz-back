import uuid

from sqlalchemy import ARRAY, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from database import Base


class HobbyActivity(Base):
    __tablename__ = "hobby_activities"

    hobby_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)  # 목록 카드용 짧은 설명
    detail_description = Column(Text, nullable=True)  # 상세 페이지 "이런 활동이에요" 긴 설명
    category = Column(String, nullable=True)  # "예술" | "운동" | "원예" 등
    tags = Column(ARRAY(String), nullable=True)  # 상세 페이지 상단 짧은 태그들 (예: ["공예","실내","초보 환영"])
    difficulty = Column(String, nullable=False, default="초급")  # "초급" | "중급" | "고급"
    image_url = Column(String, nullable=True)  # 목데이터 임시 사진(Unsplash). 실제 강좌 사진 연동 전까지 사용

    # 상세 페이지 일정 정보
    schedule = Column(String, nullable=True)  # "2026년 8월 30일 (일) 오후 2시"
    location = Column(String, nullable=True)  # "서울 마포구 모로 공방 스튜디오"
    duration = Column(String, nullable=True)  # "약 2시간"
    capacity = Column(String, nullable=True)  # "최대 8명 (소규모로 진행)"

    # 상세 페이지 "부담 수준" 3축 — 은둔·고립 성향 유저가 참여 부담을 가늠할 수 있게
    physical_burden = Column(String, nullable=True)  # "낮음" | "보통" | "높음"
    social_burden = Column(String, nullable=True)  # "없음" | "소규모" | "다수"
    preparation_burden = Column(String, nullable=True)  # "없음" | "약간" | "많음"

    conditions = Column(ARRAY(String), nullable=True)  # "참여 조건 안내" 체크리스트

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
