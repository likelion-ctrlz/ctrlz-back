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
같은 이유로 analyze_emotion_pattern() 도 LLM을 쓰지 않는 순수 함수입니다.

[라벨 체계 — 디자인 확정 기준]
감정 라벨은 편안함/설렘/불안/무기력 4종으로 고정합니다 (프론트 차트가 4개로 그려짐).

[재현성 우선]
분류·판정 호출은 전부 temperature=0 + JSON 모드로 고정했습니다.
데모 리허설과 본 발표에서 같은 입력에 다른 결과가 나오는 것을 막기 위함입니다.
"LLM을 쓰면 더 똑똑해지지 않냐"는 이유로 이 설계를 바꾸지 마세요.
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
    """OpenAI 클라이언트 지연 초기화. 키가 없으면 None 반환 → 더미 모드.

    timeout=15.0, max_retries=1 로 짧게 잡습니다. SDK 기본값(600초)이면
    데모 중 API가 늦어질 때 폴백이 바로 작동하지 않고 화면이 멈춘 것처럼 보입니다.
    """
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[AI] 경고: OPENAI_API_KEY 미설정 → 더미 모드로 동작합니다")
        return None
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=api_key, timeout=15.0, max_retries=1)
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
# 1. 미션 추천 (LLM 미사용 — 의도적 설계)
# ---------------------------------------------------------------------------

_MISSION_POOL = {
    1: [
        {"title": "창문 열고 3분 바람 쐬기", "description": "창문을 열고 3분만 바깥 공기를 느껴보세요.", "level": 1, "reward_tokens": 10},
        {"title": "커피 끓고 향만 5분 쐬기", "description": "커피를 끓이고 향기가 나는 자리에 앉아보세요.", "level": 1, "reward_tokens": 10},
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
        "reason": None,
    }


def verify_photo(image_bytes: bytes, mission_title: str,
                  conditions: list[str] | None = None) -> dict:
    """미션 인증 사진 판별.

    [설계 의도 — 비대칭 위해 설계]
    실패 판정을 최소화합니다. 어려운 상황에서 겨우 외출한 사용자에게
    '인증 실패'를 띄우는 것은 심한 트리거가 됩니다. 애매하면 통과시킵니다.
    위치·시각 검증은 사진 메타데이터로 백엔드가 담당하는 것을 권장합니다.

    Args:
        image_bytes: 이미지 원본 바이트 (S3 업로드는 백엔드 담당)
        mission_title: 수행한 미션 제목
        conditions: 미션별 인증 조건 체크리스트(선택). 백엔드가 미션 상세 화면에
            노출하는 조건 문구를 그대로 넘기면 프롬프트가 참고해서 판단합니다.
            None이면 기존과 동일하게 제목만으로 판단합니다 (하위호환 유지).

    Returns:
        {"passed": bool, "confidence": float, "comment": str, "reason": str|None}
        comment 는 판정과 무관하게 항상 긍정 문구이므로 그대로 노출 가능합니다.
        reason 은 passed=False 일 때만 값이 있습니다.
            "unclear"(어둡거나 흐려서 판독 어려움) | "not_related"(미션과 무관) | "invalid"(스크린샷 등)
    """
    client = _get_client()
    if client is None:
        return _fallback_verify(mission_title)

    try:
        b64 = base64.b64encode(image_bytes).decode()
        condition_block = "\n".join(f"- {c}" for c in conditions) if conditions else "(별도 조건 없음)"
        prompt = (
            _load_prompt("verify")
            .replace("{mission_title}", mission_title)
            .replace("{conditions}", condition_block)
        )

        res = client.chat.completions.create(
            model=VISION_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
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
        passed = bool(data.get("passed", True))
        raw_reason = data.get("reason")
        valid_reasons = {"unclear", "not_related", "invalid"}
        # 방어: 모델이 지시를 안 따르고 설명 문장 등을 넣으면 무시하고 None 처리
        reason = raw_reason if (not passed and raw_reason in valid_reasons) else None
        return {
            "passed": passed,
            "confidence": float(data.get("confidence", 0.9)),
            "comment": data.get("comment") or _fallback_verify(mission_title)["comment"],
            "reason": reason,
        }
    except Exception as e:
        print(f"[AI] verify_photo 실패, 폴백 사용: {e}")
        return _fallback_verify(mission_title)


# ---------------------------------------------------------------------------
# 3. 말하는 일기장 (STT + 감정 분석)
# ---------------------------------------------------------------------------

_FALLBACK_DIARY = {
    "text": "오늘은 창문을 열어봤다. 바람이 생각보다 차가웠지만 나쁘지 않았다.",
    "emotion": "편안함",  # 라벨 4종: 편안함/설렘/불안/무기력
    "risk_level": 0,
}

_VALID_EMOTIONS = {"편안함", "설렘", "불안", "무기력"}


def analyze_text_diary(text: str) -> dict:
    """텍스트로 바로 쓴 일기 감정 분석 (STT 없이 텍스트만 받는 경로).

    transcribe_diary() 는 STT만 수행하고 감정 분석은 이 함수에 위임합니다.

    Returns:
        {"text": str, "emotion": str, "risk_level": int}

        emotion: 편안함 | 설렘 | 불안 | 무기력
        risk_level: 0=일반, 1=주의, 2=자기위해
            ※ 2인 경우 백엔드단에서 상담 연계 안내를 응답에 포함해주세요.
    """
    text = (text or "").strip()
    if not text:
        return dict(_FALLBACK_DIARY)

    client = _get_client()
    if client is None:
        return dict(_FALLBACK_DIARY)

    try:
        prompt = _load_prompt("diary").replace("{content}", text)
        res = client.chat.completions.create(
            model=TEXT_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        data = _parse_json(res.choices[0].message.content)

        risk = int(data.get("risk_level", 0))
        raw_emotion = data.get("emotion")
        # 방어: 모델이 지시를 어기고 4종 밖의 단어를 반환하면 무시하고 기본값 처리
        # (프론트 차트가 이 4개 라벨에만 색상을 매핑하고 있어, 다른 값이 오면 깨짐)
        emotion = raw_emotion if raw_emotion in _VALID_EMOTIONS else _FALLBACK_DIARY["emotion"]
        return {
            "text": data.get("text") or text,
            "emotion": emotion,
            "risk_level": max(0, min(2, risk)),
        }
    except Exception as e:
        print(f"[AI] analyze_text_diary 실패, 폴백 사용: {e}")
        return dict(_FALLBACK_DIARY)


def transcribe_diary(audio_bytes: bytes, filename: str = "diary.m4a") -> dict:
    """음성 일기 → 텍스트 변환 + 감정 분석.

    STT만 수행하고 감정 분석은 analyze_text_diary() 에 위임합니다.
    시그니처·반환형은 기존과 동일합니다 (하위호환 유지).

    Returns:
        {"text": str, "emotion": str, "risk_level": int}
    """
    client = _get_client()
    if client is None:
        return dict(_FALLBACK_DIARY)

    try:
        audio = io.BytesIO(audio_bytes)
        audio.name = filename  # OpenAI SDK가 확장자로 포맷을 판별합니다
        stt = client.audio.transcriptions.create(
            model=STT_MODEL, file=audio, language="ko",
            temperature=0,  # Whisper도 temperature 고정 → 환각(hallucination) 최소화
        )
        text = stt.text.strip()
    except Exception as e:
        print(f"[AI] transcribe_diary STT 실패, 폴백 사용: {e}")
        return dict(_FALLBACK_DIARY)

    return analyze_text_diary(text)


def analyze_emotion_pattern(entries: list) -> dict | None:
    """감정별 최빈 시간대 분석. LLM 미사용 — 순수 함수.

    통계 산출은 결정론적 계산으로 충분하고, 데모에서는 재현성이 지능보다 중요합니다.

    Args:
        entries: [{"emotion": str, "created_at": "2026-08-18T21:30:00"}, ...]

    Returns:
        가장 자주 나타난 (감정, 시간대) 조합 하나.
        {"emotion": str, "time_slot": str, "count": int, "pattern_text": str}
        기록이 3건 미만이면 패턴을 말하기엔 이르므로 None을 반환합니다.
    """
    from collections import Counter
    from datetime import datetime

    def _time_slot(hour: int) -> str:
        if 6 <= hour < 11:
            return "아침"
        if 11 <= hour < 17:
            return "낮"
        if 17 <= hour < 22:
            return "저녁"
        return "밤"

    pairs = []
    for e in entries:
        created_at = e.get("created_at")
        emotion = e.get("emotion")
        if not created_at or not emotion:
            continue
        try:
            hour = datetime.fromisoformat(str(created_at).replace("Z", "+00:00")).hour
        except (ValueError, AttributeError):
            continue
        pairs.append((emotion, _time_slot(hour)))

    if len(pairs) < 3:
        return None

    (emotion, time_slot), count = Counter(pairs).most_common(1)[0]
    return {
        "emotion": emotion,
        "time_slot": time_slot,
        "count": count,
        "pattern_text": f"'{emotion}' 감정이 주로 {time_slot} 시간대에 많이 기록됐어요",
    }


def summarize_diary(entries: list) -> dict:
    """일기 목록 요약 + 감정 추이 + 반복 패턴 반환.

    ※ 반환형을 str → dict 로 확장했습니다.
      '최근 7일 감정 추이' 그래프를 문자열로는 데이터를 넘길 수 없습니다.

    Args:
        entries: [{"content", "emotion", "created_at"}, ...] 또는 [str, ...]

    Returns:
        {
          "summary": str,
          "trend": [{"date": str, "emotion": str}, ...],
          "pattern": {"emotion", "time_slot", "count", "pattern_text"} | None
        }
        pattern 은 데이터 3건 미만이면 None. LLM 실패와 무관하게 항상 계산됩니다
        (순수 함수라 API 장애의 영향을 받지 않음).
    """
    normalized = [
        {"content": e, "emotion": "편안함", "created_at": ""} if isinstance(e, str) else e
        for e in entries
    ]
    recent = normalized[-7:]
    trend = [
        {"date": (e.get("created_at") or "")[:10], "emotion": e.get("emotion", "편안함")}
        for e in recent
    ]
    pattern = analyze_emotion_pattern(normalized)  # 최근 7일 제한 없이 전체 기록 기준
    fallback = "이번 주에는 바깥 공기를 쐰 날이 늘었어요. 작지만 분명한 변화예요."

    client = _get_client()
    if client is None or not recent:
        return {"summary": fallback, "trend": trend, "pattern": pattern}

    try:
        joined = "\n".join(f"- {e.get('content', '')}" for e in recent)
        prompt = _load_prompt("summary").replace("{entries}", joined)
        res = client.chat.completions.create(
            model=TEXT_MODEL,
            temperature=0,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        summary = res.choices[0].message.content.strip() or fallback
        return {"summary": summary, "trend": trend, "pattern": pattern}
    except Exception as e:
        print(f"[AI] summarize_diary 실패, 폴백 사용: {e}")
        return {"summary": fallback, "trend": trend, "pattern": pattern}


def summarize_diary_text(entries: list) -> str:
    """[하위호환] 기존 str 반환 시그니처."""
    return summarize_diary(entries)["summary"]
