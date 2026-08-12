import os

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal
from models.user import User
from security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

KAKAO_USER_INFO_URL = "https://kapi.kakao.com/v2/user/me"
GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"


class KakaoLoginRequest(BaseModel):
    access_token: str


class GoogleLoginRequest(BaseModel):
    id_token: str


def _upsert_user(db: Session, *, filter_field: str, filter_value: str, email: str, nickname: str, profile_image: str) -> User:
    user = db.query(User).filter(getattr(User, filter_field) == filter_value).first()
    if user is None:
        user = User(
            **{filter_field: filter_value},
            email=email,
            nickname=nickname,
            profile_image=profile_image,
        )
        db.add(user)
    else:
        user.email = email or user.email
        user.nickname = nickname or user.nickname
        user.profile_image = profile_image or user.profile_image
    db.commit()
    db.refresh(user)
    return user


@router.post("/kakao")
async def login_kakao(payload: KakaoLoginRequest):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            KAKAO_USER_INFO_URL,
            headers={"Authorization": f"Bearer {payload.access_token}"},
        )

    if res.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="카카오 토큰이 유효하지 않습니다")

    data = res.json()
    kakao_account = data.get("kakao_account", {})
    profile = kakao_account.get("profile", {})

    db = SessionLocal()
    try:
        user = _upsert_user(
            db,
            filter_field="kakao_id",
            filter_value=str(data["id"]),
            email=kakao_account.get("email"),
            nickname=profile.get("nickname"),
            profile_image=profile.get("profile_image_url"),
        )
        token = create_access_token(user.id)
    finally:
        db.close()

    return {"status": "success", "data": {"access_token": token, "token_type": "bearer"}}


@router.post("/google")
async def login_google(payload: GoogleLoginRequest):
    async with httpx.AsyncClient() as client:
        res = await client.get(GOOGLE_TOKEN_INFO_URL, params={"id_token": payload.id_token})

    if res.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="구글 토큰이 유효하지 않습니다")

    data = res.json()

    if data.get("aud") != os.getenv("GOOGLE_CLIENT_ID"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="구글 클라이언트 정보가 일치하지 않습니다")

    db = SessionLocal()
    try:
        user = _upsert_user(
            db,
            filter_field="google_id",
            filter_value=data["sub"],
            email=data.get("email"),
            nickname=data.get("name"),
            profile_image=data.get("picture"),
        )
        token = create_access_token(user.id)
    finally:
        db.close()

    return {"status": "success", "data": {"access_token": token, "token_type": "bearer"}}
