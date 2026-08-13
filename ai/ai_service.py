"""
AI 파트 구현 영역. routers/에서 직접 import 해서 사용.

[동작 방식]
OPENAI_API_KEY 가 설정되어 있으면 실제 OpenAI 호출,
없거나 호출이 실패하면 자동으로 더미 응답으로 폴백합니다.
→ 백엔드/프론트는 AI 상태와 무관하게 항상 정상 응답을 받습니다.
→ 데모 중 네트워크 문제로 크래시만 안 나면 화면이 깨지지 않습니다.

[미션 추천은 의도적으로 LLM을 쓰지 않습니다]
매 호출마다 다른 미션이 나오면 데모 재현성이 무너지고,
난이도 곡선(레벨 1~4)이 흔들립니다. DB 없이 레벨 필터가 더 안정적입니다.
"""

import base64
import io
import json
import os
from pathlib import Path

PROMPT_DIR = Path(__file__).parent / "prompts"

# 모델명은 환경변수로 교체 가능하게 로드됩니다. 사용 가능한 모델은 확인 후 조정하세요.
VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")
TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
STT_MODEL = os.getenv("OPENAI_STT_MODEL", "whisper-1")

_client = None


def _get_client():
    """OpenAI 클라이언트 지연 초기화. 키가 없으면 None 반환 → 더미 모드."""
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=api_key)
        return _client
    except Exception:
        return None


def _load_prompt(name: str) -> str:
    """prompts/{name}.txt 로드. 프롬프트만 고치면 되므로 코드 재배포 불필요."""
    return (PROMPT_DIR / f"{name}.txt").read_text(encoding="utf-8")


def _parse_json(raw: str) -> dict:
    """LLM 응답에서 JSON 추출. 백틱이 붙어 나오는 경우를 방어합니다."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("JSON 형식 응답이 아닙니다")
    return json.loads(text[start:end + 1])


# ---------------------------------------------------------------------------
# 1. 미션 추천 (LLM 미사용 — 정주행 참고)
# ---------------------------------------------------------------------------

_MISSION_POOL = {
    1: [
        {"title": "창문 열고 3분 바람 쐬기", "description": "창문을 열고 3분만 바깥 공기를 느껴보세요.", "level": 1, "reward_tokens": 10},
        {"title": "커피 끓고 향만 5분 쐬기", "description": "커피를 끓고 향기가 나는 자리에 앉아보세요.", "level": 1, "reward_tokens": 10},
        {"title": "물 한 잔 마시기", "description": "지금 이 순간, 물 한 잔을 천천히 마셔보세요.", "level": 1, "reward_tokens": 10},
    ],
    2: [
        {"title": "현관문 밖 1분 서있기", "description": "문 밖에 1분만 서있다 들어와도 괜찮아요.", "level": 2, "reward_tokens": 20},
        {"title": "편의점 다녀오기", "description": "가까운 편의점을 다녀오세요. 아무것도 안 사도 괜찮아요.", "level": 2, "reward_tokens": 20},
        {"title": "우편함 확인하기", "description": "잠깐 나가서 우편함을 확인해보세요.", "level": 2, "reward_tokens": 20},
    ],
    3: [
        {"title": "근처 공원 다녀오기", "description": "가까운 공원까지 걸어갔다 오세요.", "level": 3, "reward_tokens": 30},
        {"title": "동네 한 바퀴 걷기", "description": "집 주변을 천천히 한 바퀴 돌아보세요.", "level": 3, "reward_tokens": 30},
        {"title": "도서관에서 책 한 권 빌리기", "description": "가까운 도서관을 들러보세요.", "level": 3, "reward_tokens": 30},
    ],
    4: [
        {"title": "동네 카페에서 15분 머물기", "description": "카페에 앉아 15분만 머물러보세요.", "level": 4, "reward_tokens": 40},
        {"title": "장 보러 마트 다녀오기", "description": "필요한 것 하나만 사와도 성공입니다.", "level": 4, "reward_tokens": 40},
        {"title": "취미 모임 한 번 참여하기", "description": "끝까지 있지 않아도 괜찮아요. 가본 것만으로 충분합니다.", "level": 4, "reward_tokens": 40},
    ],
}


def get_missions(level: int, user_type: str | None = None, count: int = 3) -> list[dict]:
    """레벨에 맞는 미션 목록 추천.

    Returns: [{"title", "description", "level", "reward_tokens"}, ...]
    """
    level = max(1, min(4, level or 1))
    return _MISSION_POOL[level][:count]


def get_mission(level: int, user_type: str) -> dict:
    """[하위호환] 기존 시그니처. 단건 반환."""
    return get_missions(level, user_type, count=1)[0]


# ---------------------------------------------------------------------------
# 2. 미션 사진 인증 (Vision)
# ---------------------------------------------------------------------------

def _fallback_verify(mission_title: str) -> dict:
    return {
        "passed": True,
        "confidence": 0.9,
        "comment": f"'{mission_title}' 다녀오셨네요. 오늘 한 걸음, 확실히 나아간 거예요.",
    }


def verify_photo(image_bytes: bytes, mission_title: str) -> dict:
    """미션 인증 사진 판별.

    [설계 의도]
    실패 판정을 최소화합니다. 어려운 상황에서 겨우 외출한 사용자에게
    '인증 실패'를 띄우는 것은 심한 트리거가 됩니다.
    위치·시각 검증은 사진 메타데이터로 백엔드가 담당하는 것을 권장합니다.

    Args:
        image_bytes: 이미지 원본 바이트 (S3 업로드된 백엔드 담당)
        mission_title: 수행한 미션 제목

    Returns:
        {"passed": bool, "confidence": float, "comment": str}
        comment 는 판정과 무관하게 항상 긍정 문구이므로 그대로 노출 가능합니다.
    """
    client = _get_client()
    if client is None:
        return _fallback_verify(mission_title)

    try:
        b64 = base64.b64encode(image_bytes).decode()
        prompt = _load_prompt("verify").replace("{mission_title}", mission_title)

        res = client.chat.completions.create(
            model=VISION_MODEL,
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            }],
        )
        data = _parse_json(res.choices[0].message.content)
        return {
            "passed": bool(data.get("passed", True)),
            "confidence": float(data.get("confidence", 0.9)),
            "comment": data.get("comment") or _fallback_verify(mission_title)["comment"],
        }
    except Exception as e:
        print(f"[AI] verify_photo 실패, 폴백 사용: {e}")
        return _fallback_verify(mission_title)


# ---------------------------------------------------------------------------
# 3. 말하는 일기장 (STT + 감정 분석)
# ---------------------------------------------------------------------------

_FALLBACK_DIARY = {
    "text": "오늘은 창문을 열어봤다. 바람이 생각보다 차가웠지만 나쁘지 않았다.",
    "emotion": "행복",
    "risk_level": 0,
}


def transcribe_diary(audio_bytes: bytes, filename: str = "diary.m4a") -> dict:
    """음성 일기 → 텍스트 변환 + 감정 분석.

    Returns:
        {"text": str, "emotion": str, "risk_level": int}

        emotion: 행복 | 무기력 | 불안 | 우울 | 긍정
        risk_level: 0=일반, 1=주의, 2=자기위해
            ※ 2인 경우 백엔드단에서 상담 연계 안내를 응답에 포함해주세요.
    """
    client = _get_client()
    if client is None:
        return dict(_FALLBACK_DIARY)

    try:
        audio = io.BytesIO(audio_bytes)
        audio.name = filename  # OpenAI SDK가 확장자로 포맷을 판별합니다
        stt = client.audio.transcriptions.create(
            model=STT_MODEL, file=audio, language="ko"
        )
        text = stt.text.strip()
        if not text:
            return dict(_FALLBACK_DIARY)

        prompt = _load_prompt("diary").replace("{content}", text)
        res = client.chat.completions.create(
            model=TEXT_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        data = _parse_json(res.choices[0].message.content)

        risk = int(data.get("risk_level", 0))
        return {
            "text": data.get("text") or text,
            "emotion": data.get("emotion", "행복"),
            "risk_level": max(0, min(2, risk)),
        }
    except Exception as e:
        print(f"[AI] transcribe_diary 실패, 폴백 사용: {e}")
        return dict(_FALLBACK_DIARY)


def summarize_diary(entries: list) -> dict:
    """일기 목록 요약 + 감정 추이 반환.

    ※ 반환형을 str → dict 로 확장했습니다.
      '최근 7일 감정 추이' 그래프를 문자열로는 데이터를 넘길 수 없습니다.

    Args:
        entries: [{"content", "emotion", "created_at"}, ...] 또는 [str, ...]

    Returns:
        {"summary": str, "trend": [{"date": str, "emotion": str}, ...]}
    """
    normalized = [
        {"content": e, "emotion": "행복", "created_at": ""} if isinstance(e, str) else e
        for e in entries
    ]
    recent = normalized[-7:]
    trend = [
        {"date": (e.get("created_at") or "")[:10], "emotion": e.get("emotion", "행복")}
        for e in recent
    ]
    fallback = "이번 주에는 바깥 공기를 쐰 날이 늘었어요. 작지만 분명한 변화예요."

    client = _get_client()
    if client is None or not recent:
        return {"summary": fallback, "trend": trend}

    try:
        joined = "\n".join(f"- {e.get('content', '')}" for e in recent)
        res = client.chat.completions.create(
            model=TEXT_MODEL,
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": (
                    "다음은 사용자의 최근 일기입니다. 2문장 이내로 요약하세요.\n"
                    "진단하거나 조언하지 말고, 변화가 있었다면 그 변화만 짚어주세요.\n"
                    "병명이나 상태를 규정하는 표현은 쓰지 마세요.\n"
                    "JSON 없이 요약 문장만 출력하세요.\n\n" + joined
                ),
            }],
        )
        summary = res.choices[0].message.content.strip() or fallback
        return {"summary": summary, "trend": trend}
    except Exception as e:
        print(f"[AI] summarize_diary 실패, 폴백 사용: {e}")
        return {"summary": fallback, "trend": trend}


def summarize_diary_text(entries: list) -> str:
    """[하위호환] 기존 str 반환 시그니처."""
    return summarize_diary(entries)["summary"]
