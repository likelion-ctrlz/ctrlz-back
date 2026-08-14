from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from ai.ai_service import verify_photo
from database import get_db
from dependencies import get_current_user
from models.mission import Mission, MissionCompletion
from models.token import TokenTransaction, TokenWallet
from models.user import User
from services.s3 import upload_file

router = APIRouter(prefix="/missions", tags=["missions"])


@router.get("/recommended")
def get_recommended_missions(
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    # 미션 추천은 DB 필터링 사용 (AI 미션 풀 미사용 확정)
    query = db.query(Mission).filter(Mission.is_active.is_(True))
    if current_user.status_level is not None:
        query = query.filter(Mission.target_level.any(current_user.status_level))
    if current_user.user_type is not None:
        query = query.filter(Mission.target_type.any(current_user.user_type))

    missions = query.limit(limit).all()

    data = [
        {
            "mission_id": str(m.mission_id),
            "title": m.title,
            "description": m.description,
            "difficulty": m.difficulty,
            "category": m.category,
            "verification_type": m.verification_type,
            "token_reward": m.token_reward,
        }
        for m in missions
    ]

    return {"status": "success", "data": data}


@router.post("/{mission_id}/submit")
async def submit_mission(
    mission_id: str,
    photo: UploadFile = File(...),
    gps_lat: float = Form(...),
    gps_lng: float = Form(...),
    taken_at: datetime = Form(...),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    mission = db.get(Mission, mission_id)
    if mission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="미션을 찾을 수 없습니다")

    completion = MissionCompletion(
        user_id=current_user.user_id,
        mission_id=mission.mission_id,
        status="ai_processing",
    )
    db.add(completion)
    db.flush()

    photo_bytes = await photo.read()
    photo_url = upload_file(
        photo_bytes,
        key=f"missions/{current_user.user_id}/{completion.completion_id}.jpg",
        content_type=photo.content_type or "image/jpeg",
    )

    verdict = verify_photo(photo_bytes, mission.title)
    ai_verdict = verdict["passed"]
    ai_feedback = verdict["comment"]

    completion.photo_url = photo_url
    completion.photo_gps_lat = gps_lat
    completion.photo_gps_lng = gps_lng
    completion.photo_taken_at = taken_at
    completion.ai_verdict = ai_verdict
    completion.ai_feedback = ai_feedback

    token_balance = None
    if ai_verdict:
        completion.status = "approved"
        completion.token_earned = mission.token_reward
        completion.completed_at = datetime.utcnow()

        wallet = db.get(TokenWallet, current_user.user_id)
        wallet.token_balance += mission.token_reward
        db.add(TokenTransaction(
            user_id=current_user.user_id,
            amount=mission.token_reward,
            reason="mission_complete",
            ref_id=completion.completion_id,
        ))
        token_balance = wallet.token_balance
    else:
        completion.status = "rejected"

    db.commit()

    return {
        "status": "success",
        "data": {
            "completion_id": str(completion.completion_id),
            "ai_verdict": ai_verdict,
            "ai_feedback": ai_feedback,
            "token_earned": completion.token_earned,
            "token_balance": token_balance,
        },
    }


@router.get("/{mission_id}/result")
def get_mission_result(
    mission_id: str,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    completion = (
        db.query(MissionCompletion)
        .filter(
            MissionCompletion.mission_id == mission_id,
            MissionCompletion.user_id == current_user.user_id,
        )
        .order_by(MissionCompletion.created_at.desc())
        .first()
    )
    if completion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인증 기록을 찾을 수 없습니다")

    return {
        "status": "success",
        "data": {
            "completion_id": str(completion.completion_id),
            "status": completion.status,
            "ai_verdict": completion.ai_verdict,
            "ai_feedback": completion.ai_feedback,
            "token_earned": completion.token_earned,
        },
    }


@router.get("/history")
def get_mission_history(
    date: str | None = None,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    query = db.query(MissionCompletion).filter(MissionCompletion.user_id == current_user.user_id)
    if date:
        query = query.filter(func.date(MissionCompletion.completed_at) == date)

    completions = query.order_by(MissionCompletion.created_at.desc()).all()

    data = [
        {
            "completion_id": str(c.completion_id),
            "mission_title": c.mission.title if c.mission else None,
            "status": c.status,
            "token_earned": c.token_earned,
            "completed_at": c.completed_at,
        }
        for c in completions
    ]

    return {"status": "success", "data": data}
