"""
공공데이터포털 - 서울특별시교육청 평생학습포털 에버러닝 강좌정보 서비스 연동.

hobbies.py(취미활동)와 programs.py(지역 지원 프로그램) 둘 다 이 API를 데이터 소스로 씁니다.
(programs 쪽은 실제 "지역 연계 기관" 성격과는 다소 결이 다를 수 있어 임시로 붙여둔 것 —
 더 맞는 데이터 소스가 생기면 fetch_programs()만 교체하면 됩니다.)

오퍼레이션: getLectureList (실제 호출로 확인 완료). 응답은 type 파라미터와 무관하게 XML 고정.

[동작 방식]
API 키가 없거나, 호출/파싱이 실패하면 자동으로 큐레이션된 더미 데이터로 폴백합니다.
→ 라우터는 이 함수들이 항상 정상적인 리스트를 반환한다고 가정하고 써도 됩니다.
→ 데모 중 공공API가 느리거나 응답 안 해도 화면이 깨지지 않습니다.
"""

import os
import xml.etree.ElementTree as ET
from itertools import zip_longest

import httpx

BASE_URL = "https://apis.data.go.kr/7010000/everlearning"
OPERATION = os.getenv("EVERLEARNING_OPERATION", "getLectureList")
API_KEY = os.getenv("EVERLEARNING_API_KEY")

_EXCLUDED_TARGETS = {"영유아", "유아", "어린이", "초등학생", "중학생", "청소년"}
_EXCLUDED_TITLE_KEYWORDS = ("영유아", "어린이", "유아", "초등", "중학생", "학년", "청소년")


def _is_for_children_or_students(item: ET.Element) -> bool:
    target = (item.findtext("targetNm") or "").strip()
    if target in _EXCLUDED_TARGETS:
        return True

    title = (item.findtext("lectureNm") or "")
    return any(kw in title for kw in _EXCLUDED_TITLE_KEYWORDS)


def _diversify_by_category(items: list[ET.Element]) -> list[ET.Element]:
    """카테고리별로 묶은 뒤 라운드로빈으로 섞어서 한 카테고리에 몰리지 않게 한다."""
    groups: dict[str, list[ET.Element]] = {}
    for item in items:
        cat = (item.findtext("categoryNm") or "").strip() or "기타"
        groups.setdefault(cat, []).append(item)

    interleaved = []
    for row in zip_longest(*groups.values()):
        interleaved.extend(x for x in row if x is not None)
    return interleaved


def _fetch_filtered_items(num_of_rows: int, region: str | None = None) -> list[ET.Element] | None:
    """공통 호출: 아동/학생 대상 제외 + 카테고리 다양화까지 마친 item 목록.

    실패하거나 결과가 없으면 None (호출부에서 각자의 폴백 데이터를 쓰도록).
    """
    if not API_KEY:
        return None

    try:
        # 카테고리 분포가 고르지 않아(인문교양이 절반 이상) 다양성을 확보하려면
        # 꽤 넉넉하게 가져와야 시민참여/학력보완처럼 드문 카테고리도 섞인다.
        fetch_rows = max(num_of_rows * 20, 200)
        res = httpx.get(
            f"{BASE_URL}/{OPERATION}",
            params={"serviceKey": API_KEY, "pageNo": 1, "numOfRows": fetch_rows},
            timeout=8.0,
        )
        res.raise_for_status()

        root = ET.fromstring(res.text)
        result_code = root.findtext("./header/resultCode")
        if result_code != "00":
            print(f"[everlearning] API 에러 응답, 폴백 사용: {root.findtext('./header/resultMsg')}")
            return None

        items = [
            item for item in root.findall("./body/items/item")
            if not _is_for_children_or_students(item)
        ]
        if region:
            region_matched = [item for item in items if region in (item.findtext("sigunguNm") or "")]
            items = region_matched or items  # 지역 매칭 결과가 없으면 전체에서라도 뽑는다

        if not items:
            return None

        return _diversify_by_category(items)
    except Exception as e:
        print(f"[everlearning] 호출 실패, 폴백 사용: {e}")
        return None


# ---------------------------------------------------------------------------
# 취미활동 (hobbies.py)
# ---------------------------------------------------------------------------

_FALLBACK_HOBBIES = [
    {
        "title": "실내 원예 모임",
        "description": "소규모 원예 활동을 함께해요.",
        "detail_description": (
            "작은 화분에 씨앗이나 모종을 직접 심고 가꾸는 법을 배우는 모임이에요.\n"
            "말을 많이 하지 않아도 괜찮아요, 흙을 만지는 시간 자체가 목적이에요."
        ),
        "category": "원예",
        "tags": ["원예", "실내", "초보 환영"],
        "difficulty": "초급",
        "image_url": "https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=600",
        "schedule": "매주 화요일 오후 3시",
        "location": "서울 마포구 모로 커뮤니티룸",
        "duration": "약 1시간 30분",
        "capacity": "최대 6명 (소규모로 진행)",
        "physical_burden": "낮음",
        "social_burden": "소규모",
        "preparation_burden": "없음",
        "conditions": [
            "재료(화분·모종) 포함, 별도 준비물 없어요",
            "참여 취소는 하루 전까지 가능해요",
            "중간에 조용히 나가도 괜찮아요",
        ],
        "token_cost": 30,
    },
    {
        "title": "도자기 공방 체험",
        "description": "손으로 흙을 빚으며 마음을 가라앉혀보세요.",
        "detail_description": (
            "손으로 흙을 빚으며 집중과 이완을 동시에 경험할 수 있는 클래스예요.\n"
            "별도 경험이 없어도 강사가 처음부터 함께 도와드려요."
        ),
        "category": "공예",
        "tags": ["공예", "실내", "초보 환영"],
        "difficulty": "초급",
        "image_url": "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?w=600",
        "schedule": "매주 목요일 오후 2시",
        "location": "서울 마포구 모로 공방 스튜디오",
        "duration": "약 2시간",
        "capacity": "최대 8명 (소규모로 진행)",
        "physical_burden": "낮음",
        "social_burden": "소규모",
        "preparation_burden": "없음",
        "conditions": [
            "재료비 포함, 별도 준비물 없어요",
            "참여 취소는 하루 전까지 가능해요",
            "사진 촬영은 자유이며 공유 의무는 없어요",
        ],
        "token_cost": 40,
    },
    {
        "title": "가벼운 스트레칭 모임",
        "description": "무리 없는 동작으로 몸을 움직여봐요.",
        "detail_description": (
            "앉거나 누운 채로도 할 수 있는 가벼운 스트레칭 위주로 진행돼요.\n"
            "체력이 부담스러워도 눈치 볼 필요 없이 본인 속도로 따라가면 돼요."
        ),
        "category": "운동",
        "tags": ["운동", "실내", "저체력 가능"],
        "difficulty": "초급",
        "image_url": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=600",
        "schedule": "매주 월·수 오전 11시",
        "location": "서울 마포구 모로 커뮤니티룸",
        "duration": "약 40분",
        "capacity": "최대 10명",
        "physical_burden": "낮음",
        "social_burden": "소규모",
        "preparation_burden": "없음",
        "conditions": [
            "편한 복장이면 충분해요, 운동복 없어도 괜찮아요",
            "매트는 현장에서 대여 가능해요",
            "참여 취소는 하루 전까지 가능해요",
        ],
        "token_cost": 20,
    },
    {
        "title": "드로잉 클래스",
        "description": "그림 도구만 있으면 누구나 참여할 수 있어요.",
        "detail_description": (
            "정해진 주제 없이 그리고 싶은 걸 자유롭게 그려보는 시간이에요.\n"
            "그림 실력은 상관없어요, 손을 움직이며 생각을 비우는 게 목적이에요."
        ),
        "category": "예술",
        "tags": ["예술", "실내", "자유 참여"],
        "difficulty": "중급",
        "image_url": "https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=600",
        "schedule": "매주 금요일 오후 4시",
        "location": "서울 마포구 모로 아트룸",
        "duration": "약 1시간 30분",
        "capacity": "최대 8명 (소규모로 진행)",
        "physical_burden": "낮음",
        "social_burden": "소규모",
        "preparation_burden": "약간",
        "conditions": [
            "기본 드로잉 도구는 현장에 준비돼 있어요",
            "원하는 스케치북·펜이 있다면 직접 가져와도 좋아요",
            "참여 취소는 하루 전까지 가능해요",
        ],
        "token_cost": 25,
    },
    {
        "title": "캘리그라피 클래스",
        "description": "펜 하나로 나만의 손글씨체를 만들어가는 시간이에요.",
        "detail_description": (
            "펜과 잉크로 한 글자 한 글자 정성껏 써보는 시간이에요.\n"
            "처음이어도 괜찮아요, 삐뚤빼뚤한 글씨도 나만의 개성이 될 수 있어요."
        ),
        "category": "예술",
        "tags": ["예술", "실내", "초보 환영"],
        "difficulty": "중급",
        "image_url": "https://images.unsplash.com/photo-1455390582262-044cdead277a?w=600",
        "schedule": "매주 토요일 오후 1시",
        "location": "서울 성동구 모로 아트룸",
        "duration": "약 1시간 30분",
        "capacity": "최대 6명 (소규모로 진행)",
        "physical_burden": "낮음",
        "social_burden": "소규모",
        "preparation_burden": "없음",
        "conditions": [
            "펜과 잉크는 현장에 준비돼 있어요",
            "원하는 필기구가 있다면 가져와도 좋아요",
            "참여 취소는 하루 전까지 가능해요",
        ],
        "token_cost": 25,
    },
    {
        "title": "홈베이킹 원데이클래스",
        "description": "따뜻한 빵 냄새로 채우는 나만의 시간이에요.",
        "detail_description": (
            "반죽부터 굽기까지 처음부터 끝까지 직접 만들어보는 클래스예요.\n"
            "서툴러도 괜찮아요, 완성된 빵을 직접 맛보는 재미가 있어요."
        ),
        "category": "요리",
        "tags": ["요리", "실내", "초보 환영"],
        "difficulty": "초급",
        "image_url": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600",
        "schedule": "매주 일요일 오전 11시",
        "location": "서울 마포구 모로 베이킹 스튜디오",
        "duration": "약 2시간",
        "capacity": "최대 6명 (소규모로 진행)",
        "physical_burden": "낮음",
        "social_burden": "소규모",
        "preparation_burden": "없음",
        "conditions": [
            "재료·도구 모두 현장에 준비돼 있어요",
            "완성한 빵은 포장해서 가져갈 수 있어요",
            "참여 취소는 하루 전까지 가능해요",
        ],
        "token_cost": 35,
    },
    {
        "title": "손글씨 필사 모임",
        "description": "좋아하는 문장을 천천히 옮겨 적어보는 시간이에요.",
        "detail_description": (
            "마음에 드는 책의 한 구절을 골라 손으로 천천히 옮겨 적어봐요.\n"
            "말없이 각자의 속도로 써 내려가는 조용한 시간이에요."
        ),
        "category": "글쓰기",
        "tags": ["글쓰기", "실내", "조용한 활동"],
        "difficulty": "초급",
        "image_url": "https://images.unsplash.com/photo-1517842645767-c639042777db?w=600",
        "schedule": "매주 수요일 오후 7시",
        "location": "서울 마포구 모로 라운지",
        "duration": "약 1시간",
        "capacity": "최대 8명",
        "physical_burden": "낮음",
        "social_burden": "없음",
        "preparation_burden": "없음",
        "conditions": [
            "필기구와 노트는 현장에 준비돼 있어요",
            "대화 없이 조용히 진행돼요",
            "참여 취소는 하루 전까지 가능해요",
        ],
        "token_cost": 15,
    },
    {
        "title": "필름카메라 사진 산책",
        "description": "천천히 걸으며 눈에 담은 순간을 사진으로 남겨요.",
        "detail_description": (
            "동네를 산책하며 마음에 드는 순간을 필름카메라로 찍어봐요.\n"
            "잘 찍지 않아도 괜찮아요, 카메라를 들고 밖을 걸어본 것 자체가 의미 있어요."
        ),
        "category": "예술",
        "tags": ["예술", "외출", "가벼운 활동"],
        "difficulty": "초급",
        "image_url": "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=600",
        "schedule": "매주 토요일 오전 10시",
        "location": "서울 마포구 모로 스튜디오 앞 집결",
        "duration": "약 1시간 30분",
        "capacity": "최대 6명 (소규모로 진행)",
        "physical_burden": "보통",
        "social_burden": "소규모",
        "preparation_burden": "없음",
        "conditions": [
            "카메라는 현장에서 대여 가능해요(개인 카메라도 환영)",
            "무리해서 걷지 않아도 괜찮아요",
            "참여 취소는 하루 전까지 가능해요",
        ],
        "token_cost": 30,
    },
    {
        "title": "요가 기초반",
        "description": "숨을 고르며 몸과 마음을 천천히 풀어봐요.",
        "detail_description": (
            "기초 동작 위주로 무리 없이 진행되는 요가 수업이에요.\n"
            "유연하지 않아도 괜찮아요, 내 호흡에 맞춰 천천히 따라가면 돼요."
        ),
        "category": "운동",
        "tags": ["운동", "실내", "초보 환영"],
        "difficulty": "초급",
        "image_url": "https://images.unsplash.com/photo-1575052814086-f385e2e2ad1b?w=600",
        "schedule": "매주 화·목 오전 10시",
        "location": "서울 마포구 모로 요가룸",
        "duration": "약 50분",
        "capacity": "최대 10명",
        "physical_burden": "보통",
        "social_burden": "소규모",
        "preparation_burden": "없음",
        "conditions": [
            "매트는 현장에서 대여 가능해요",
            "편한 복장이면 충분해요",
            "참여 취소는 하루 전까지 가능해요",
        ],
        "token_cost": 20,
    },
    {
        "title": "라떼아트 커피 클래스",
        "description": "한 잔의 커피에 그림을 그려보는 시간이에요.",
        "detail_description": (
            "우유 스티밍부터 라떼아트까지 차근차근 배워보는 클래스예요.\n"
            "처음엔 모양이 안 나와도 괜찮아요, 직접 만든 커피 한 잔의 여유를 느껴봐요."
        ),
        "category": "요리",
        "tags": ["요리", "실내", "초보 환영"],
        "difficulty": "중급",
        "image_url": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=600",
        "schedule": "매주 금요일 오후 3시",
        "location": "서울 마포구 모로 카페 스튜디오",
        "duration": "약 1시간 30분",
        "capacity": "최대 6명 (소규모로 진행)",
        "physical_burden": "낮음",
        "social_burden": "소규모",
        "preparation_burden": "없음",
        "conditions": [
            "원두와 도구는 현장에 준비돼 있어요",
            "만든 커피는 그 자리에서 맛볼 수 있어요",
            "참여 취소는 하루 전까지 가능해요",
        ],
        "token_cost": 30,
    },
    {
        "title": "다육이 분갈이 클래스",
        "description": "작은 화분에 다육식물을 옮겨 심어보는 시간이에요.",
        "detail_description": (
            "여러 다육식물 중 마음에 드는 걸 골라 직접 분갈이해보는 클래스예요.\n"
            "집에 작은 생명체 하나를 데려와보는 건 어때요."
        ),
        "category": "원예",
        "tags": ["원예", "실내", "초보 환영"],
        "difficulty": "초급",
        "image_url": "https://images.unsplash.com/photo-1459156212016-c812468e2115?w=600",
        "schedule": "매주 일요일 오후 2시",
        "location": "서울 마포구 모로 가든룸",
        "duration": "약 1시간",
        "capacity": "최대 8명",
        "physical_burden": "낮음",
        "social_burden": "소규모",
        "preparation_burden": "없음",
        "conditions": [
            "화분과 다육식물은 현장에 준비돼 있어요",
            "완성한 화분은 가져갈 수 있어요",
            "참여 취소는 하루 전까지 가능해요",
        ],
        "token_cost": 25,
    },
    {
        "title": "보드게임 소모임",
        "description": "말 없이도 함께 즐길 수 있는 가벼운 모임이에요.",
        "detail_description": (
            "규칙이 쉬운 보드게임으로 가볍게 어울려보는 모임이에요.\n"
            "처음 만난 사람과도 게임을 매개로 자연스럽게 시간을 보낼 수 있어요."
        ),
        "category": "사회활동",
        "tags": ["사회활동", "실내", "가벼운 참여"],
        "difficulty": "초급",
        "image_url": "https://images.unsplash.com/photo-1610890716171-6b1bb98ffd09?w=600",
        "schedule": "매주 토요일 오후 6시",
        "location": "서울 마포구 모로 라운지",
        "duration": "약 2시간",
        "capacity": "최대 8명",
        "physical_burden": "낮음",
        "social_burden": "소규모",
        "preparation_burden": "없음",
        "conditions": [
            "게임 규칙은 진행자가 쉽게 설명해줘요",
            "꼭 말을 많이 하지 않아도 괜찮아요",
            "참여 취소는 하루 전까지 가능해요",
        ],
        "token_cost": 15,
    },
]


def _item_to_hobby(item: ET.Element) -> dict:
    def text(tag: str) -> str:
        el = item.find(tag)
        return (el.text or "").strip() if el is not None else ""

    place = text("place")
    teacher = text("teacherNm")
    organ = text("organNm")
    parts = [p for p in (organ, f"강사 {teacher}" if teacher else "", place) if p]
    category = text("categoryNm") or "평생학습"

    return {
        "title": text("lectureNm") or "강좌",
        "description": " · ".join(parts),
        "detail_description": None,  # API가 긴 소개문을 안 줘서 상세 페이지에선 description으로 대체
        "category": category,
        "tags": [category],
        "difficulty": "초급",  # API가 난이도를 안 줘서 기본값. 실제 강좌 사진도 없어 image_url은 None
        "image_url": None,
        "schedule": None,
        "location": place or None,
        "duration": None,
        "capacity": None,
        "physical_burden": None,
        "social_burden": None,
        "preparation_burden": None,
        "conditions": None,
        "token_cost": 30,
    }


def fetch_hobby_courses(num_of_rows: int = 10) -> list[dict]:
    """에버러닝 강좌 목록 조회.

    Returns: 취미활동 딕셔너리 목록. 목록 카드용(title/description/category/difficulty/image_url/token_cost)과
    상세 페이지용(detail_description/tags/schedule/location/duration/capacity/*_burden/conditions) 필드를 모두 포함.
    API가 안 주는 상세 필드는 None — 실제 강좌 상세 정보가 없기 때문에 지어내지 않음.
    실패 시 항상 큐레이션된 더미 데이터를 반환 (예외를 던지지 않음).
    """
    items = _fetch_filtered_items(num_of_rows)
    if items is None:
        return list(_FALLBACK_HOBBIES)
    return [_item_to_hobby(item) for item in items[:num_of_rows]]


# ---------------------------------------------------------------------------
# 지역 지원 프로그램·기관 (programs.py)
# ---------------------------------------------------------------------------

_FALLBACK_PROGRAMS = [
    {
        "title": "강동구 평생학습 강좌 둘러보기",
        "agency_name": "강동구평생학습관",
        "region": "서울 강동구",
        "description": "강동구평생학습관에서 지금 열려있는 다양한 강좌를 둘러보고 신청할 수 있어요. 관심 가는 주제 하나만 골라봐도 좋아요.",
        "image_url": "https://images.unsplash.com/photo-1455390582262-044cdead277a?w=600",
        "contact": "02-XXX-XXXX",
        "apply_url": "https://lll.gangdong.go.kr/main/Main.do",
    },
    {
        "title": "드로잉 클래스",
        "agency_name": "마포구 평생학습포털(공예작업실)",
        "region": "서울 마포구",
        "description": "정해진 주제 없이 손 가는 대로 그려보는 자유로운 시간이에요. 그림 실력은 상관없어요, 그리는 행위 자체에 집중해봐요.",
        "image_url": "https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=600",
        "contact": "02-XXX-XXXX",
        "apply_url": "https://www.mapo.go.kr/site/mll/edu/lecture_view?ltSeq=14963&cp=1&pageSize=9&listType=list&lgtSeq=LG001",
    },
    {
        "title": "마음돌봄 인문교실",
        "agency_name": "은평구평생학습관",
        "region": "서울 은평구",
        "description": "책과 이야기를 통해 나를 천천히 돌아보는 인문학 강좌예요. 무거운 주제 없이 편안하게 듣고 나누는 시간이에요.",
        "image_url": "https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=600",
        "contact": "02-XXX-XXXX",
        "apply_url": "https://edu.eunpyeong.go.kr/edu/read2.nx?M2_IDX=15022&SHOW_TYPE=NORMAL&page=1&EP_IDX=28671&EM_IDX=28509",
    },
    {
        "title": "필라테스 기초반",
        "agency_name": "노원구시설관리공단 월계구민체육센터",
        "region": "서울 노원구",
        "description": "기초 동작 위주로 무리 없이 진행되는 필라테스 수업이에요. 체력이 부담스러워도 본인 속도로 편하게 따라가면 돼요.",
        "image_url": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=600",
        "contact": "02-XXX-XXXX",
        "apply_url": "https://www.nowonsc.kr/fmcs/188?center=NOWON02&action=read&page=1&comcd=NOWON02&classcd=00097&type=R",
    },
    {
        "title": "성동문화재단 강좌 둘러보기",
        "agency_name": "성동문화재단",
        "region": "서울 성동구",
        "description": "성동문화재단에서 지금 열려있는 강좌를 둘러보고 신청할 수 있어요. 글쓰기, 캘리그라피 등 다양한 주제가 있어요.",
        "image_url": "https://images.unsplash.com/photo-1517842645767-c639042777db?w=600",
        "contact": "02-XXX-XXXX",
        "apply_url": "https://edu.sdfac.or.kr/www/selectUserLectureList.do?key=708&aCode=SDDLIB",
    },
    {
        "title": "캘리그라피 클래스",
        "agency_name": "오금동 자치회관(송파런)",
        "region": "서울 송파구",
        "description": "펜과 잉크로 한 글자 한 글자 정성껏 써보는 시간이에요. 처음이어도 괜찮아요, 삐뚤빼뚤한 글씨도 나만의 개성이 될 수 있어요.",
        "image_url": "https://images.unsplash.com/photo-1455390582262-044cdead277a?w=600",
        "contact": "02-XXX-XXXX",
        "apply_url": "https://www.songpa.go.kr/learn/youth/program/lecture_view.do?lecture_idx=16873",
    },
    {
        "title": "서대문구 평생학습 강좌 둘러보기",
        "agency_name": "서대문구 평생학습포털",
        "region": "서울 서대문구",
        "description": "서대문구 평생학습포털에서 지금 접수 중인 강좌를 둘러보고 신청할 수 있어요. 글쓰기, 명상 등 다양한 주제가 있어요.",
        "image_url": "https://images.unsplash.com/photo-1517842645767-c639042777db?w=600",
        "contact": "02-XXX-XXXX",
        "apply_url": "https://www.sdm.go.kr/lll/user/lectureinfo/lectureInfoList.do",
    },
    {
        "title": "서울청년센터 광진 프로그램 둘러보기",
        "agency_name": "서울청년센터 광진",
        "region": "서울 광진구",
        "description": "서울청년센터 광진에서 진행하는 다양한 프로그램을 둘러보고 신청할 수 있어요. 사진, 문화 활동 등 여러 주제가 있어요.",
        "image_url": "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=600",
        "contact": "02-XXX-XXXX",
        "apply_url": "https://youth.seoul.go.kr/orang/infoData/sprtInfo/list.do?key=2309210005",
    },
    {
        "title": "강서구 생활체육 프로그램 둘러보기",
        "agency_name": "강서구공공체육시설",
        "region": "서울 강서구",
        "description": "강서구 생활체육시설에서 지금 열려있는 운동 프로그램을 둘러보고 신청할 수 있어요. 무리 없는 종목부터 골라봐도 좋아요.",
        "image_url": "https://images.unsplash.com/photo-1575052814086-f385e2e2ad1b?w=600",
        "contact": "02-XXX-XXXX",
        "apply_url": "https://sports.gangseo.seoul.kr/fmcs/102",
    },
    {
        "title": "동작구 문화·체육 프로그램 둘러보기",
        "agency_name": "동작구시설관리공단",
        "region": "서울 동작구",
        "description": "동작구시설관리공단에서 진행하는 다양한 문화·체육 프로그램을 둘러보고 신청할 수 있어요.",
        "image_url": "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?w=600",
        "contact": "02-XXX-XXXX",
        "apply_url": "https://sports.idongjak.or.kr/home/171",
    },
    {
        "title": "구로문화예술아카데미 강좌 둘러보기",
        "agency_name": "구로문화재단",
        "region": "서울 구로구",
        "description": "구로문화재단에서 지금 열려있는 문화예술 강좌를 둘러보고 신청할 수 있어요.",
        "image_url": "https://images.unsplash.com/photo-1459156212016-c812468e2115?w=600",
        "contact": "02-XXX-XXXX",
        "apply_url": "https://www.guroartsvalley.or.kr/",
    },
    {
        "title": "관악청년청 프로그램 둘러보기",
        "agency_name": "관악청년청",
        "region": "서울 관악구",
        "description": "관악청년청에서 진행하는 다양한 프로그램을 둘러보고 신청할 수 있어요. 마음 돌봄부터 자기계발까지 다양해요.",
        "image_url": "https://images.unsplash.com/photo-1610890716171-6b1bb98ffd09?w=600",
        "contact": "02-XXX-XXXX",
        "apply_url": "https://www.checkin-gwanak.or.kr/core/?cid=29",
    },
]


def _item_to_program(item: ET.Element) -> dict:
    def text(tag: str) -> str:
        el = item.find(tag)
        return (el.text or "").strip() if el is not None else ""

    sigungu = text("sigunguNm")

    return {
        "title": text("lectureNm") or "지역 프로그램",
        "agency_name": text("organNm"),
        "region": f"서울 {sigungu}" if sigungu else None,
        "description": f"장소: {text('place')}" if text("place") else "",
        "image_url": None,  # API가 사진을 안 줘서 지어내지 않고 비워둠
        "contact": text("contactInfo") or text("organTelNo") or None,
        "apply_url": None,
    }


def fetch_programs(region: str | None = None, num_of_rows: int = 10) -> list[dict]:
    """지역 지원 프로그램·기관 목록 조회 (임시로 에버러닝 강좌 데이터를 재활용).

    Returns: [{"title", "agency_name", "region", "description", "contact", "apply_url"}, ...]
    실패 시 항상 큐레이션된 더미 데이터를 반환 (예외를 던지지 않음).
    """
    # region은 "서울 종로구" 형태로 들어올 수 있어 구 이름만 추출해 매칭
    sigungu = region.split()[-1] if region else None
    items = _fetch_filtered_items(num_of_rows, region=sigungu)
    if items is None:
        return list(_FALLBACK_PROGRAMS)
    return [_item_to_program(item) for item in items[:num_of_rows]]
