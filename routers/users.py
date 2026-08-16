import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from database import get_db
from dependencies import get_current_user
from models.mission import Mission, MissionCompletion
from models.token import TokenWallet
from models.user import User
from services.character import CHARACTER_STAGES, MAX_LEVEL, XP_THRESHOLDS
from services.missions import difficulty_range_for_level

router = APIRouter(prefix="/users", tags=["users"])


class UserUpdateRequest(BaseModel):
    region: str | None = Field(None, description="거주 지역 (시·구 단위)", examples=["서울 마포구"])


def _today_recommended_mission(db: DBSession, user: User) -> dict | None:
    today = datetime.now(timezone.utc).date()
    done_today = {
        str(c.mission_id)
        for c in db.query(MissionCompletion).filter(
            MissionCompletion.user_id == user.user_id,
            MissionCompletion.status == "approved",
        )
        if c.completed_at and c.completed_at.date() == today
    }

    lo, hi = difficulty_range_for_level(user.assessment_level)
    query = db.query(Mission).filter(
        Mission.is_active.is_(True),
        Mission.difficulty >= lo,
        Mission.difficulty <= hi,
    )

    candidates = [m for m in query.all() if str(m.mission_id) not in done_today]
    if not candidates:
        return None

    if user.is_demo:
        wow_candidates = [m for m in candidates if m.is_wow]
        if wow_candidates:
            candidates = wow_candidates

    seed = f"{user.user_id}:today:{today.isoformat()}"
    idx = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(candidates)
    mission = candidates[idx]

    return {
        "mission_id": str(mission.mission_id),
        "title": mission.title,
        "token_reward": mission.token_reward,
        "xp_reward": mission.xp_reward,
        "difficulty": mission.difficulty,
    }


@router.get(
    "/me",
    summary="내 프로필 조회",
    description="닉네임, 지역, 자가진단 결과, 캐릭터(모로) 상태, 토큰 잔액, 오늘의 추천 미션까지 한 번에 반환합니다. 홈 화면용 엔드포인트입니다.",
)
def get_me(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    wallet = db.get(TokenWallet, current_user.user_id)

    level = current_user.character_level
    next_threshold = XP_THRESHOLDS[level] if level < MAX_LEVEL else None
    xp_next_level = next_threshold if next_threshold is not None else current_user.character_xp

    return {
        "status": "success",
        "data": {
            "user_id": str(current_user.user_id),
            "nickname": current_user.nickname,
            "region": current_user.region,
            "is_demo": current_user.is_demo,

            "assessment_level": current_user.assessment_level,
            "assessment_type": current_user.assessment_type,
            "assessment_score": current_user.assessment_score,

            "character_level": current_user.character_level,
            "character_xp": current_user.character_xp,
            "character_xp_next_level": xp_next_level,
            "character_image": CHARACTER_STAGES[level]["image"],

            "token_balance": wallet.token_balance if wallet else 0,

            "today_recommended_mission": _today_recommended_mission(db, current_user),
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
