"""
레벨별 더미 미션 시드 데이터.

실제 미션 기획이 나오면 이 파일의 MISSIONS 리스트만 교체하면 됩니다.
(missions.py 라우터는 DB를 그대로 조회하므로 코드 변경 불필요)

실행: python seed_missions.py
"""

import uuid

from database import Base, SessionLocal, engine
from models.mission import Mission

ALL_TYPES = ["은둔형", "고립형", "복합형", "관찰군"]

MISSIONS = [
    # Level 1
    {
        "title": "창문 열고 3분 바람 쐬기",
        "description": "창문을 열고 3분만 바깥 공기를 느껴보세요.",
        "difficulty": 1,
        "category": "자기관리",
        "target_level": [1],
        "verification_type": "photo",
        "token_reward": 10,
    },
    {
        "title": "물 한 잔 마시기",
        "description": "지금 이 순간, 물 한 잔을 천천히 마셔보세요.",
        "difficulty": 1,
        "category": "자기관리",
        "target_level": [1],
        "verification_type": "text",
        "token_reward": 10,
    },
    {
        "title": "커피 내리고 향 맡기",
        "description": "커피를 내리고 향이 나는 자리에 앉아보세요.",
        "difficulty": 1,
        "category": "자기관리",
        "target_level": [1],
        "verification_type": "photo",
        "token_reward": 10,
    },
    # Level 2
    {
        "title": "현관문 밖 1분 서있기",
        "description": "문 밖에 1분만 서있다 들어와도 괜찮아요.",
        "difficulty": 2,
        "category": "외출",
        "target_level": [2],
        "verification_type": "photo",
        "token_reward": 20,
    },
    {
        "title": "편의점 다녀오기",
        "description": "가까운 편의점을 다녀오세요. 아무것도 안 사도 괜찮아요.",
        "difficulty": 2,
        "category": "외출",
        "target_level": [2],
        "verification_type": "photo",
        "token_reward": 20,
    },
    {
        "title": "우편함 확인하기",
        "description": "잠깐 나가서 우편함을 확인해보세요.",
        "difficulty": 2,
        "category": "외출",
        "target_level": [2],
        "verification_type": "photo",
        "token_reward": 20,
    },
    # Level 3
    {
        "title": "근처 공원 다녀오기",
        "description": "가까운 공원까지 걸어갔다 오세요.",
        "difficulty": 3,
        "category": "외출",
        "target_level": [3],
        "verification_type": "photo",
        "token_reward": 30,
    },
    {
        "title": "동네 한 바퀴 걷기",
        "description": "집 주변을 천천히 한 바퀴 돌아보세요.",
        "difficulty": 3,
        "category": "외출",
        "target_level": [3],
        "verification_type": "photo",
        "token_reward": 30,
    },
    # Level 4
    {
        "title": "동네 카페에서 15분 머물기",
        "description": "카페에 앉아 15분만 머물러보세요.",
        "difficulty": 4,
        "category": "관계",
        "target_level": [4],
        "verification_type": "photo",
        "token_reward": 40,
    },
    {
        "title": "장 보러 마트 다녀오기",
        "description": "필요한 것 하나만 사와도 성공입니다.",
        "difficulty": 4,
        "category": "외출",
        "target_level": [4],
        "verification_type": "photo",
        "token_reward": 40,
    },
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(Mission).count()
        if existing > 0:
            print(f"missions 테이블에 이미 {existing}건 있어 스킵합니다.")
            return

        for m in MISSIONS:
            db.add(Mission(mission_id=uuid.uuid4(), target_type=ALL_TYPES, is_active=True, **m))
        db.commit()
        print(f"{len(MISSIONS)}건 시드 완료")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
