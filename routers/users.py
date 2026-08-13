from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from database import get_db
from dependencies import get_current_user
from models.token import TokenWallet
from models.user import User

router = APIRouter(prefix="/users", tags=["users"])


class UserUpdateRequest(BaseModel):
    region: str | None = None


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    wallet = db.get(TokenWallet, current_user.user_id)

    return {
        "status": "success",
        "data": {
            "user_id": str(current_user.user_id),
            "nickname": current_user.nickname,
            "region": current_user.region,
            "status_level": current_user.status_level,
            "user_type": current_user.user_type,
            "token_balance": wallet.token_balance if wallet else 0,
        },
    }


@router.patch("/me")
def update_me(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    if payload.region is not None:
        current_user.region = payload.region
    db.commit()

    return {"status": "success", "data": {"region": current_user.region}}
