"""취미활동 큐레이션 시드 데이터 (services/everlearning.py의 _FALLBACK_HOBBIES).

에버러닝 공공API가 정상 응답하면 GET /hobbies/recommended가 그쪽 데이터를 우선 쓰기 때문에,
이 큐레이션 데이터(실제 사진·상세정보 포함)가 노출되려면 DB에 미리 심어둬야 함
(missions처럼 "DB에 없으면 API 폴백" 순서라 시딩 없이는 절대 안 보임).

실행: python seed_hobbies.py
"""

import uuid

from database import Base, SessionLocal, engine
from models.hobby import HobbyActivity
from services.everlearning import _FALLBACK_HOBBIES

ALL_LEVELS = [1, 2, 3, 4]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(HobbyActivity).count()
        if existing > 0:
            print(f"hobby_activities 테이블에 이미 {existing}건 있어 스킵합니다.")
            return

        for h in _FALLBACK_HOBBIES:
            db.add(HobbyActivity(
                hobby_id=uuid.uuid4(),
                recommended_level=ALL_LEVELS,
                is_active=True,
                **h,
            ))
        db.commit()
        print(f"{len(_FALLBACK_HOBBIES)}건 시드 완료")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
