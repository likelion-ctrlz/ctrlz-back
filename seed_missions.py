"""PM 미션 기획 반영 시드 데이터.

실행: python seed_missions.py

[난이도 배정 메모]
난이도 스케일은 1~7 (services/missions.py의 LEVEL_DIFFICULTY_MAP과 짝을 맞춤:
레벨1→1~3, 레벨2→3~5, 레벨3→4~6, 레벨4→5~7).
PM이 준 목록은 원래 1~4 난이도로 왔고, 아래 선형 변환(1→1, 2→3, 3→5, 4→7)으로
새 스케일에 맞게 재배정함.

번호가 없던 3개는 같은 섹션(레벨대) 안에서 원래 1~4 스케일 기준 난이도를 추론해 채운 뒤 변환함:
  - 코인노래방 90점 받기 → 레벨3~4 섹션, 다른 항목(3,4,4,4) 균형 맞춰 원난이도 3 → 새 난이도 5
  - 산책하며 길고양이 사진 찍기 → 레벨1~2 섹션, 캐모마일티(1)보다 외출 부담 있어 원난이도 2 → 새 난이도 3
  - 침대·책상 위치 바꾸기 → 레벨1~2 섹션, 실내 활동이라 캐모마일티와 동급인 원난이도 1 → 새 난이도 1

<기존> 4개(베라/즉석복권/무인아이스크림/편의점 신상 리뷰)는 기존 와우포인트(is_wow) 미션과
동일 소재라 is_wow=True 유지, 난이도는 PM 지정값(4/2/2/3)을 변환한 7/3/3/5.

target_level은 더 이상 추천 필터링에 쓰이지 않고(필터링은 difficulty 범위로 직접 함),
난이도가 어느 자가진단 레벨 구간에 걸치는지 보여주는 정보성 필드로만 채워둠.
"""

import uuid

from database import Base, SessionLocal, engine
from models.mission import Mission
from services.missions import target_levels_for_difficulty

ALL_TYPES = ["은둔형", "고립형", "복합형", "관찰군"]

MISSIONS = [
    # ── <기존> 와우포인트 미션 (데모 모드 우선 노출) ── 원난이도 4/2/2/3 → 새 난이도 7/3/3/5
    {
        "title": "베라에서 이달의 맛 시도하기",
        "description": "이달의 신메뉴 맛, 궁금하지 않았나요?",
        "detail_description": (
            "가까운 배스킨라빈스에 들러 이달의 맛을 한 스쿱 주문해보세요.\n"
            "처음 먹어보는 맛이라도 괜찮아요, 새로운 걸 시도해본 것 자체가 오늘의 미션이에요."
        ),
        "difficulty": 7,
        "category": "외출",
        "verification_type": "photo",
        "conditions": [
            "매장 안 또는 매장 앞에서 촬영한 사진이어야 해요",
            "구매한 아이스크림(또는 영수증)이 보여야 해요",
            "오늘 날짜의 실시간 사진만 인정 돼요",
        ],
        "xp_reward": 10,
        "token_reward": 20,
        "bonus_token": 0,
        "is_wow": True,
    },
    {
        "title": "즉석복권 사기",
        "description": "혼자서도 할 수 있는 작은 외출이에요.",
        "detail_description": (
            "집 앞이나 편의점에서 즉석복권 한 장을 사보세요.\n"
            "큰돈 들이지 않고도 오늘 하루에 작은 설렘을 더할 수 있어요.\n"
            "당첨이 안 돼도 괜찮아요, 문 밖을 나선 것 자체가 오늘의 미션이에요."
        ),
        "difficulty": 3,
        "category": "외출",
        "verification_type": "photo",
        "conditions": [
            "야외 또는 매장에서 촬영한 사진이어야 해요",
            "구매한 복권이 보여야 해요",
            "오늘 날짜의 실시간 사진만 인정 돼요",
        ],
        "xp_reward": 30,
        "token_reward": 20,
        "bonus_token": 5,
        "is_wow": True,
    },
    {
        "title": "무인아이스크림 털기",
        "description": "무인매장이라 부담 없이 다녀올 수 있어요.",
        "detail_description": (
            "가까운 무인 아이스크림 할인점에 들러 마음에 드는 걸 골라보세요.\n"
            "사람과 마주치지 않아도 괜찮은 공간이라 첫 외출로도 좋아요."
        ),
        "difficulty": 3,
        "category": "외출",
        "verification_type": "photo",
        "conditions": [
            "매장 안에서 촬영한 사진이어야 해요",
            "고른 아이스크림이 보여야 해요",
            "오늘 날짜의 실시간 사진만 인정 돼요",
        ],
        "xp_reward": 10,
        "token_reward": 20,
        "bonus_token": 0,
        "is_wow": True,
    },
    {
        "title": "편의점 신상 리뷰",
        "description": "요즘 나온 신상 궁금하지 않았나요?",
        "detail_description": (
            "편의점에서 아직 안 먹어본 신상품을 하나 골라보세요.\n"
            "맛이 있든 없든 솔직한 한 줄 후기를 남기면 완료예요."
        ),
        "difficulty": 5,
        "category": "외출",
        "verification_type": "photo",
        "conditions": [
            "매장 안 또는 구매 후 촬영한 사진이어야 해요",
            "고른 신상품이 보여야 해요",
            "오늘 날짜의 실시간 사진만 인정 돼요",
        ],
        "xp_reward": 20,
        "token_reward": 30,
        "bonus_token": 5,
        "is_wow": True,
    },

    # ── <레벨 1~2> ── 원난이도 1/1/2 → 새 난이도 1/1/3
    {
        "title": "집에서 캐모마일티 만들어 마시기",
        "description": "티백 하나로 시작하는 작은 루틴이에요.",
        "detail_description": (
            "캐모마일티(없으면 다른 티백도 괜찮아요)를 우려 천천히 마셔보세요.\n"
            "집 밖으로 나가지 않아도 되는, 나를 위한 가장 작은 미션이에요."
        ),
        "difficulty": 1,
        "category": "자기관리",
        "verification_type": "photo",
        "conditions": [
            "우려낸 티(찻잔)가 보이는 사진이어야 해요",
            "오늘 날짜의 실시간 사진만 인정 돼요",
        ],
        "xp_reward": 10,
        "token_reward": 10,
        "bonus_token": 0,
        "is_wow": False,
    },
    {
        "title": "침대와 책상 위치 바꿔보기",
        "description": "공간이 바뀌면 기분도 조금 달라져요.",
        "detail_description": (
            "방 안 침대와 책상의 위치를 바꿔보세요. 완전히 재배치하지 않아도 괜찮아요.\n"
            "매일 보던 풍경이 조금 달라지는 것만으로도 충분한 변화예요."
        ),
        "difficulty": 1,
        "category": "자기관리",
        "verification_type": "photo",
        "conditions": [
            "바뀐 배치가 보이는 방 사진이어야 해요",
            "오늘 날짜의 실시간 사진만 인정 돼요",
        ],
        "xp_reward": 10,
        "token_reward": 10,
        "bonus_token": 0,
        "is_wow": False,
    },
    {
        "title": "산책하면서 길고양이 찾아서 사진찍기",
        "description": "가볍게 걸으며 주변을 둘러보는 미션이에요.",
        "detail_description": (
            "동네를 산책하다 길고양이를 발견하면 사진으로 남겨보세요.\n"
            "고양이를 못 만나도 괜찮아요, 산책하며 주변을 둘러본 사진이면 인정돼요."
        ),
        "difficulty": 3,
        "category": "외출",
        "verification_type": "photo",
        "conditions": [
            "야외에서 촬영한 사진이어야 해요",
            "길고양이 또는 산책 중인 주변 환경이 보여야 해요",
            "오늘 날짜의 실시간 사진만 인정 돼요",
        ],
        "xp_reward": 20,
        "token_reward": 20,
        "bonus_token": 0,
        "is_wow": False,
    },

    # ── <레벨 3~4> ── 원난이도 3/3/4/4/4 → 새 난이도 5/5/7/7/7
    {
        "title": "꽃집가서 다육이 사고 이름짓기",
        "description": "작은 생명체를 하나 데려와보는 건 어때요.",
        "detail_description": (
            "근처 꽃집(화원)에 들러 다육이 한 개를 사보세요.\n"
            "집에 데려온 다육이에게 이름을 지어주면 미션 완료예요."
        ),
        "difficulty": 5,
        "category": "외출",
        "verification_type": "photo",
        "conditions": [
            "구매한 다육이가 보이는 사진이어야 해요",
            "매장 안 또는 집에서 촬영한 사진이어야 해요",
            "오늘 날짜의 실시간 사진만 인정 돼요",
        ],
        "xp_reward": 30,
        "token_reward": 30,
        "bonus_token": 0,
        "is_wow": False,
    },
    {
        "title": "코인노래방가서 90점 이상 받아보기",
        "description": "목청껏 불러보는 것도 오랜만이죠.",
        "detail_description": (
            "가까운 코인노래방에서 좋아하는 노래를 골라 불러보세요.\n"
            "90점을 못 넘겨도 괜찮아요, 부스에 들어가 한 곡 완창한 것 자체가 미션이에요."
        ),
        "difficulty": 5,
        "category": "외출",
        "verification_type": "photo",
        "conditions": [
            "코인노래방 부스 안 또는 점수 화면이 보이는 사진이어야 해요",
            "오늘 날짜의 실시간 사진만 인정 돼요",
        ],
        "xp_reward": 30,
        "token_reward": 30,
        "bonus_token": 0,
        "is_wow": False,
    },
    {
        "title": "집 앞 아무 버스나 타보기",
        "description": "목적지 없는 외출도 괜찮은 외출이에요.",
        "detail_description": (
            "집 앞 정류장에서 아무 버스나 골라 타고 종점까지 가보세요.\n"
            "어디로 가는지 몰라도 괜찮아요, 낯선 동네를 구경하고 돌아오면 완료예요."
        ),
        "difficulty": 7,
        "category": "외출",
        "verification_type": "photo",
        "conditions": [
            "버스 안 또는 종점에서 촬영한 사진이어야 해요",
            "오늘 날짜의 실시간 사진만 인정 돼요",
        ],
        "xp_reward": 40,
        "token_reward": 40,
        "bonus_token": 0,
        "is_wow": False,
    },
    {
        "title": "올리브영 가서 최애 향수 찾아보기",
        "description": "나에게 어울리는 향을 찾아 떠나는 짧은 외출.",
        "detail_description": (
            "올리브영에 들러 향수 테스터를 자유롭게 시향해보세요.\n"
            "구매하지 않아도 괜찮아요, 가장 마음에 드는 향 하나를 찾아보면 완료예요."
        ),
        "difficulty": 7,
        "category": "외출",
        "verification_type": "photo",
        "conditions": [
            "매장 안에서 촬영한 사진이어야 해요",
            "고른 향수(테스터)가 보여야 해요",
            "오늘 날짜의 실시간 사진만 인정 돼요",
        ],
        "xp_reward": 40,
        "token_reward": 40,
        "bonus_token": 0,
        "is_wow": False,
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
            target_level = target_levels_for_difficulty(m["difficulty"])
            db.add(Mission(
                mission_id=uuid.uuid4(),
                target_type=ALL_TYPES,
                target_level=target_level,
                is_active=True,
                **m,
            ))
        db.commit()
        print(f"{len(MISSIONS)}건 시드 완료")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
