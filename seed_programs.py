"""지역 지원 프로그램·기관 큐레이션 시드 데이터 (services/everlearning.py의 _FALLBACK_PROGRAMS).

에버러닝 공공API가 정상 응답하면 GET /programs가 그쪽 데이터를 우선 쓰기 때문에,
이 큐레이션 데이터가 노출되려면 DB에 미리 심어둬야 함
(hobbies와 동일하게 "DB에 없으면 API 폴백" 순서라 시딩 없이는 절대 안 보임).

실행: python seed_programs.py
"""

import uuid

from database import Base, SessionLocal, engine
from models.program import Program
from services.everlearning import _FALLBACK_PROGRAMS

ALL_TYPES = ["은둔형", "고립형", "복합형", "관찰군"]
ALL_LEVELS = [1, 2, 3, 4]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(Program).count()
        if existing > 0:
            print(f"programs 테이블에 이미 {existing}건 있어 스킵합니다.")
            return

        for p in _FALLBACK_PROGRAMS:
            db.add(Program(
                program_id=uuid.uuid4(),
                target_type=ALL_TYPES,
                target_level=ALL_LEVELS,
                is_active=True,
                **p,
            ))
        db.commit()
        print(f"{len(_FALLBACK_PROGRAMS)}건 시드 완료")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
