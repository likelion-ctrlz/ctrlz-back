from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models.session import Session
from models.token import TokenWallet
from models.user import User
from security import generate_session_token, session_expiry

router = APIRouter(prefix="/session", tags=["session"])


class SessionCreateRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=30)


@router.post("")
def create_session(payload: SessionCreateRequest, db: DBSession = Depends(get_db)):
    user = User(nickname=payload.nickname)
    db.add(user)
    db.flush()

    db.add(TokenWallet(user_id=user.user_id, token_balance=0))

    session = Session(
        user_id=user.user_id,
        token=generate_session_token(),
        expires_at=session_expiry(),
    )
    db.add(session)
    db.commit()

    return {
        "status": "success",
        "data": {
            "session_token": session.token,
            "user_id": str(user.user_id),
            "nickname": user.nickname,
        },
    }
