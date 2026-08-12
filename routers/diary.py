from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models.diary import DiaryEntry
from models.user import User

router = APIRouter(prefix="/diary", tags=["diary"])


class DiaryEntryRequest(BaseModel):
    content: str
    mood: str | None = None


@router.post("/entries")
def create_diary_entry(
    payload: DiaryEntryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = DiaryEntry(
        user_id=current_user.id,
        content=payload.content,
        mood=payload.mood,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "status": "success",
        "data": {"id": entry.id, "content": entry.content, "mood": entry.mood},
    }


@router.get("/summary")
def get_diary_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # TODO: AI 연동 필요 — 확정 전까지는 최근 엔트리 개수만 반환하는 Mock 값
    entry_count = (
        db.query(DiaryEntry).filter(DiaryEntry.user_id == current_user.id).count()
    )

    return {
        "status": "success",
        "data": {"entry_count": entry_count, "summary": "AI 연동 전 Mock 요약입니다."},
    }
