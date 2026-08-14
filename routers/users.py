from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from database import get_db
from dependencies import get_current_user
from models.token import TokenWallet
from models.user import User

router = APIRouter(prefix="/users", tags=["users"])


class UserUpdateRequest(BaseModel):
    region: str | None = Field(None, description="거주 지역 (시·구 단위)", examples=["서울 마포구"])


@router.get(
    "/me",
    summary="내 프로필 조회",
    description="닉네임, 지역, 자가진단 레벨/유형, 현재 토큰 잔액까지 한 번에 반환합니다. 마이페이지 화면용 엔드포인트입니다.",
)
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


@router.patch(
    "/me",
    summary="내 프로필 수정",
    description="현재는 `region`(거주 지역)만 수정 가능합니다. 지역 정보는 `GET /programs`의 지역 매칭에 사용됩니다.",
)
def update_me(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    if payload.region is not None:
        current_user.region = payload.region
    db.commit()

    return {"status": "success", "data": {"region": current_user.region}}
