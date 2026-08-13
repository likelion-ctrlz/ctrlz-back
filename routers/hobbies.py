import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from database import get_db
from dependencies import get_current_user
from models.hobby import HobbyActivity, HobbyParticipation
from models.token import TokenTransaction, TokenWallet
from models.user import User

router = APIRouter(prefix="/hobbies", tags=["hobbies"])


@router.get("/recommended")
def get_recommended_hobbies(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    # TODO: AI 연동 필요 — 현재는 DB 필터링으로 대체
    query = db.query(HobbyActivity).filter(HobbyActivity.is_active.is_(True))
    if current_user.status_level is not None:
        query = query.filter(HobbyActivity.recommended_level.any(current_user.status_level))

    hobbies = query.all()

    data = [
        {
            "hobby_id": str(h.hobby_id),
            "title": h.title,
            "description": h.description,
            "category": h.category,
            "token_cost": h.token_cost,
        }
        for h in hobbies
    ]

    return {"status": "success", "data": data}


@router.post("/{hobby_id}/apply")
def apply_hobby(
    hobby_id: str,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    hobby = db.get(HobbyActivity, hobby_id)
    if hobby is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="취미활동을 찾을 수 없습니다")

    wallet = db.get(TokenWallet, current_user.user_id)
    if wallet is None or wallet.token_balance < hobby.token_cost:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="토큰 잔액이 부족합니다")

    participation = HobbyParticipation(
        participation_id=uuid.uuid4(),
        user_id=current_user.user_id,
        hobby_id=hobby.hobby_id,
        token_used=hobby.token_cost,
    )
    db.add(participation)

    wallet.token_balance -= hobby.token_cost
    db.add(TokenTransaction(
        user_id=current_user.user_id,
        amount=-hobby.token_cost,
        reason="hobby_apply",
        ref_id=participation.participation_id,
    ))
    db.commit()

    return {
        "status": "success",
        "data": {
            "participation_id": str(participation.participation_id),
            "status": participation.status,
            "token_used": participation.token_used,
            "token_balance": wallet.token_balance,
        },
    }
