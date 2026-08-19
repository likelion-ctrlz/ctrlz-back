from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from database import get_db
from demo import is_demo_nickname
from dependencies import bearer_scheme
from models.session import Session
from models.token import TokenWallet
from models.user import User
from security import generate_session_token, session_expiry

router = APIRouter(prefix="/session", tags=["session"])


class SessionCreateRequest(BaseModel):
    nickname: str = Field(
        min_length=1,
        max_length=30,
        description="사용자가 온보딩 화면에서 입력하는 닉네임. 실명·소셜 ID를 저장하지 않는 익명 식별자입니다. 중복 허용.",
        examples=["숲속고양이"],
    )


@router.post(
    "",
    summary="닉네임으로 온보딩 (회원가입 겸 로그인)",
    description=(
        "닉네임만 입력받아 새 유저를 생성하고 세션 토큰을 발급합니다. "
        "소셜 로그인이 없으므로 이 요청 하나로 온보딩이 끝납니다.\n\n"
        "내부적으로 `users` 레코드와 잔액 0짜리 `token_wallets` 레코드를 함께 생성합니다.\n\n"
        "응답으로 받은 `session_token`을 클라이언트에 저장하고, "
        "이후 모든 인증 필요 요청에 `Authorization: Bearer {session_token}` 헤더로 사용하세요. "
        "토큰은 발급일로부터 30일간 유효합니다."
    ),
)
def create_session(payload: SessionCreateRequest, db: DBSession = Depends(get_db)):
    # 같은 닉네임으로 다시 로그인하면 새 계정을 또 만들지 않고 기존 계정을 그대로 재사용
    # (닉네임이 사실상 유일 식별자로 쓰이는 무소셜 로그인 구조라, 재로그인할 때마다
    # 계정이 새로 생기면 이전 기록·토큰·미션 이력을 잃어버리게 됨)
    user = db.query(User).filter(User.nickname == payload.nickname).first()
    if user is None:
        user = User(nickname=payload.nickname, is_demo=is_demo_nickname(payload.nickname))
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
            "is_demo": user.is_demo,
        },
    }


@router.delete(
    "",
    summary="로그아웃",
    description=(
        "`Authorization: Bearer {session_token}` 헤더로 넘어온 세션을 서버에서 즉시 삭제합니다. "
        "이후 같은 토큰으로는 인증이 필요한 요청을 보낼 수 없습니다.\n\n"
        "이미 만료되었거나 존재하지 않는 토큰으로 호출해도 에러 없이 성공 처리됩니다 "
        "(로그아웃은 '이미 로그아웃된 상태'도 성공으로 취급하는 게 자연스럽기 때문)."
    ),
)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: DBSession = Depends(get_db),
):
    db.query(Session).filter(Session.token == credentials.credentials).delete()
    db.commit()

    return {"status": "success", "data": {"message": "로그아웃되었습니다"}}
