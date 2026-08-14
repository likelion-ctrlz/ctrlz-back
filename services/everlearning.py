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
    {"title": "실내 원예 모임", "description": "소규모 원예 활동을 함께해요.", "category": "원예", "token_cost": 30},
    {"title": "도자기 공방 체험", "description": "손으로 흙을 빚으며 마음을 가라앉혀보세요.", "category": "공예", "token_cost": 40},
    {"title": "가벼운 스트레칭 모임", "description": "무리 없는 동작으로 몸을 움직여봐요.", "category": "운동", "token_cost": 20},
    {"title": "드로잉 클래스", "description": "그림 도구만 있으면 누구나 참여할 수 있어요.", "category": "예술", "token_cost": 25},
]


def _item_to_hobby(item: ET.Element) -> dict:
    def text(tag: str) -> str:
        el = item.find(tag)
        return (el.text or "").strip() if el is not None else ""

    place = text("place")
    teacher = text("teacherNm")
    organ = text("organNm")
    parts = [p for p in (organ, f"강사 {teacher}" if teacher else "", place) if p]

    return {
        "title": text("lectureNm") or "강좌",
        "description": " · ".join(parts),
        "category": text("categoryNm") or "평생학습",
        "token_cost": 30,
    }


def fetch_hobby_courses(num_of_rows: int = 10) -> list[dict]:
    """에버러닝 강좌 목록 조회.

    Returns: [{"title", "description", "category", "token_cost"}, ...]
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
        "title": "서울시 고립·은둔청년 지원사업",
        "agency_name": "서울청년기지개센터",
        "region": "서울 종로구",
        "description": "1:1 맞춤상담, 자조모임, 외출 동행 등 고립·은둔 청년을 위한 활동형 프로그램을 제공합니다.",
        "contact": "02-XXX-XXXX",
        "apply_url": "https://youthcenter.seoul.go.kr",
    },
    {
        "title": "청년 마음건강 바우처 지원사업",
        "agency_name": "지역 정신건강복지센터",
        "region": "서울 마포구",
        "description": "심리상담 비용을 바우처로 지원합니다. 우울·불안 등 정서적 어려움을 겪는 청년이 대상입니다.",
        "contact": "02-XXX-XXXX",
        "apply_url": "https://www.mentalhealth.go.kr",
    },
    {
        "title": "청년 자립준비 지원 프로그램",
        "agency_name": "지역 청년센터",
        "region": "경기 수원시",
        "description": "구직·생활 자립을 위한 코칭과 소규모 그룹 활동을 함께 운영합니다.",
        "contact": "031-XXX-XXXX",
        "apply_url": "https://www.youthcenter.go.kr",
    },
    {
        "title": "은둔형 외톨이 회복 지원 프로그램",
        "agency_name": "지역자활센터",
        "region": "부산 해운대구",
        "description": "느린 걸음도 괜찮은 단계별 회복 프로그램. 외출-관계-자립 순으로 진행됩니다.",
        "contact": "051-XXX-XXXX",
        "apply_url": "https://www.busan.go.kr",
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
