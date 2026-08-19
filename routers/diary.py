from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session as DBSession

from ai.ai_service import analyze_text_diary, summarize_diary, transcribe_diary
from database import get_db
from dependencies import get_current_user
from models.diary import DiaryEntry
from models.user import User
from services.diary import compute_emotion_stats
from services.s3 import upload_file

router = APIRouter(prefix="/diary", tags=["diary"])


@router.post(
    "/entries",
    summary="일기 등록 (음성 또는 텍스트)",
    description=(
        "말하는 일기장에 한 건을 등록합니다. `audio`와 `text_content` 중 하나는 반드시 있어야 합니다.\n\n"
        "**음성(`audio`)으로 등록 시**: S3에 업로드 후 OpenAI Whisper로 STT 변환 + GPT로 감정 분석까지 자동 처리됩니다. "
        "감정 분석 결과 `risk_level`이 2(자기위해 신호)면 `risk_flag=True`로 저장됩니다 "
        "(현재 별도 위기대응 알림 로직은 없고 플래그만 저장).\n\n"
        "**텍스트(`text_content`)로 등록 시**: STT 없이 GPT로 감정 분석까지 자동 처리됩니다. "
        "마찬가지로 `risk_level`이 2면 `risk_flag=True`로 저장됩니다."
    ),
)
async def create_diary_entry(
    audio: UploadFile | None = File(None, description="음성 일기 파일 (m4a/webm 등). text_content와 배타적이지 않지만 보통 둘 중 하나만 사용"),
    text_content: str | None = Form(None, description="텍스트로 직접 입력한 일기 내용. audio가 없을 때 필수"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    if audio is None and not text_content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="audio 또는 text_content 중 하나는 필요합니다",
        )

    entry = DiaryEntry(user_id=current_user.user_id, text_content=text_content)
    db.add(entry)
    db.flush()

    if audio is not None:
        audio_bytes = await audio.read()
        entry.audio_url = upload_file(
            audio_bytes,
            key=f"diary/{current_user.user_id}/{entry.entry_id}.webm",
            content_type=audio.content_type or "audio/webm",
        )
        result = transcribe_diary(audio_bytes, filename=audio.filename or "diary.m4a")
        entry.transcript = result["text"]
        entry.emotion_summary = {"primary": result["emotion"], "score": {}}
        entry.risk_flag = result["risk_level"] >= 2
    else:
        result = analyze_text_diary(text_content)
        entry.transcript = result["text"]
        entry.emotion_summary = {"primary": result["emotion"], "score": {}}
        entry.risk_flag = result["risk_level"] >= 2

    db.commit()

    return {
        "status": "success",
        "data": {
            "entry_id": str(entry.entry_id),
            "transcript": entry.transcript,
            "emotion_summary": entry.emotion_summary,
            "risk_flag": entry.risk_flag,
            "created_at": entry.created_at,
        },
    }


@router.get(
    "/entries",
    summary="일기 목록 조회",
    description="본인이 작성한 일기를 최신순으로 반환합니다. 다른 유저의 일기는 조회할 수 없습니다.",
)
def list_diary_entries(
    limit: int = Query(10, description="반환할 최대 일기 개수"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    entries = (
        db.query(DiaryEntry)
        .filter(DiaryEntry.user_id == current_user.user_id)
        .order_by(DiaryEntry.created_at.desc())
        .limit(limit)
        .all()
    )

    data = [
        {
            "entry_id": str(e.entry_id),
            "transcript": e.transcript,
            "emotion_summary": e.emotion_summary,
            "created_at": e.created_at,
        }
        for e in entries
    ]

    return {"status": "success", "data": data}


@router.get(
    "/summary",
    summary="최근 N일 감정 추이 요약",
    description=(
        "최근 `days`일간의 일기를 모아 감정 추이(`emotion_trend`), 감정별 비율(`emotion_percentages`), "
        "가장 자주 기록된 감정(`most_frequent_emotion`), AI가 생성한 한두 문장짜리 요약(`ai_summary`), "
        "반복되는 감정 패턴(`pattern`)을 반환합니다. "
        "AI 요약은 진단·조언 없이 변화만 짚어주는 톤으로 생성됩니다 (병명·상태 규정 표현 금지)."
    ),
)
def get_diary_summary(
    days: int = Query(7, description="집계할 기간(일). 최근 이 기간 내 등록된 일기까지 포함"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    entries = (
        db.query(DiaryEntry)
        .filter(DiaryEntry.user_id == current_user.user_id)
        .order_by(DiaryEntry.created_at.desc())
        .limit(days)
        .all()
    )

    ai_input = [
        {
            "content": e.transcript or "",
            "emotion": (e.emotion_summary or {}).get("primary", "편안함"),
            "created_at": e.created_at.isoformat() if e.created_at else "",
        }
        for e in reversed(entries)
    ]
    result = summarize_diary(ai_input)
    emotion_trend = [{"date": t["date"], "primary": t["emotion"]} for t in result["trend"]]
    stats = compute_emotion_stats(result["trend"])

    return {
        "status": "success",
        "data": {
            "period": f"최근 {days}일",
            "emotion_trend": emotion_trend,
            "most_frequent_emotion": stats["most_frequent_emotion"],
            "emotion_percentages": stats["emotion_percentages"],
            "ai_summary": result["summary"],
            "pattern": result["pattern"],
        },
    }
