from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models.mission import Mission, MissionSubmission
from models.user import User

router = APIRouter(prefix="/missions", tags=["missions"])


class MissionSubmitRequest(BaseModel):
    content: str | None = None


@router.get("/recommended")
def get_recommended_missions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # TODO: AI 연동 필요 — 확정 전까지는 user_type 기준으로 DB에서 조회
    missions = (
        db.query(Mission)
        .filter(Mission.user_type == current_user.user_type)
        .limit(5)
        .all()
    )

    data = [
        {
            "id": m.id,
            "title": m.title,
            "description": m.description,
            "level": m.level,
            "reward_tokens": m.reward_tokens,
        }
        for m in missions
    ]

    return {"status": "success", "data": data}


@router.post("/{mission_id}/submit")
def submit_mission(
    mission_id: int,
    payload: MissionSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mission = db.get(Mission, mission_id)
    if mission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="미션을 찾을 수 없습니다")

    submission = MissionSubmission(
        mission_id=mission.id,
        user_id=current_user.id,
        content=payload.content,
    )
    db.add(submission)

    current_user.token_balance += mission.reward_tokens
    db.commit()
    db.refresh(submission)

    return {
        "status": "success",
        "data": {
            "submission_id": submission.id,
            "reward_tokens": mission.reward_tokens,
            "token_balance": current_user.token_balance,
        },
    }
