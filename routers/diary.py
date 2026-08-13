from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session as DBSession

from database import get_db
from dependencies import get_current_user
from models.diary import DiaryEntry
from models.user import User
from services.s3 import upload_file

router = APIRouter(prefix="/diary", tags=["diary"])


@router.post("/entries")
async def create_diary_entry(
    audio: UploadFile | None = File(None),
    text_content: str | None = Form(None),
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

    # TODO: AI 연동 필요 — ai.ai_service.summarize_diary 구현되면 STT/감정분석 연결, 그 전까지는 Mock 처리
    entry.transcript = text_content or "음성 인식 결과 (Mock)"
    entry.emotion_summary = {"primary": "평온", "score": {}}
    entry.risk_flag = False
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


@router.get("/entries")
def list_diary_entries(
    limit: int = 10,
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


@router.get("/summary")
def get_diary_summary(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    # TODO: AI 연동 필요 — ai.ai_service.summarize_diary 구현되면 연결, 그 전까지는 Mock 처리
    entries = (
        db.query(DiaryEntry)
        .filter(DiaryEntry.user_id == current_user.user_id)
        .order_by(DiaryEntry.created_at.desc())
        .limit(days)
        .all()
    )

    emotion_trend = [
        {
            "date": e.created_at.date().isoformat() if e.created_at else None,
            "primary": (e.emotion_summary or {}).get("primary"),
        }
        for e in reversed(entries)
    ]

    return {
        "status": "success",
        "data": {
            "period": f"최근 {days}일",
            "emotion_trend": emotion_trend,
            "ai_summary": "AI 연동 예정",
        },
    }
