import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from ai.ai_service import verify_photo
from database import get_db
from dependencies import get_current_user
from models.mission import Mission, MissionCompletion
from models.token import TokenTransaction, TokenWallet
from models.user import User
from services.character import check_level_up
from services.missions import difficulty_range_for_level
from services.s3 import upload_file

router = APIRouter(prefix="/missions", tags=["missions"])


def _deterministic_order(missions: list[Mission], user_id) -> list[Mission]:
    """유저마다 다른 순서로 섞이되, 같은 유저는 항상 같은 순서가 나오도록 결정론적으로 정렬."""
    def sort_key(mission: Mission) -> str:
        return hashlib.md5(f"{user_id}:{mission.mission_id}".encode()).hexdigest()

    return sorted(missions, key=sort_key)


def _completed_today_mission_ids(db: DBSession, user_id) -> set[str]:
    today = datetime.now(timezone.utc).date()
    completions = (
        db.query(MissionCompletion)
        .filter(
            MissionCompletion.user_id == user_id,
            MissionCompletion.status == "approved",
        )
        .all()
    )
    return {
        str(c.mission_id)
        for c in completions
        if c.completed_at and c.completed_at.date() == today
    }


def _serialize_mission(mission: Mission) -> dict:
    return {
        "mission_id": str(mission.mission_id),
        "title": mission.title,
        "description": mission.description,
        "difficulty": mission.difficulty,
        "category": mission.category,
        "verification_type": mission.verification_type,
        "xp_reward": mission.xp_reward,
        "token_reward": mission.token_reward,
        "bonus_token": mission.bonus_token,
        "is_wow": mission.is_wow,
    }


@router.get(
    "/recommended",
    summary="추천 미션 목록 조회",
    description=(
        "유저의 자가진단 레벨(`assessment_level`)에 맞는 난이도 범위의 미션 목록을 반환합니다.\n\n"
        "**레벨별 난이도 범위** (난이도 스케일 1~7, 인접 레벨끼리 구간이 겹치도록 설계):\n"
        "레벨1 → 1~3 / 레벨2 → 3~5 / 레벨3 → 4~6 / 레벨4 → 5~7. "
        "자가진단 미완료 유저는 전체 난이도(1~7)를 노출합니다.\n\n"
        "오늘 이미 승인(approved)된 미션은 후보에서 제외합니다. "
        "데모 모드 유저는 `is_wow=True` 미션을 목록 앞쪽에 우선 배치합니다.\n\n"
        "후보를 `user_id` 해시로 결정론적으로 정렬해 유저마다 다른 순서로 보이게 하되, "
        "같은 유저는 새로고침해도 항상 같은 순서·결과를 봅니다.\n\n"
        "AI 기반 추천이 아니라 DB 필터링을 사용합니다 (재현성·난이도 곡선 안정성을 위해 의도된 설계)."
    ),
)
def get_recommended_missions(
    limit: int = Query(5, ge=1, le=20, description="반환할 최대 미션 개수"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    done_today = _completed_today_mission_ids(db, current_user.user_id)

    lo, hi = difficulty_range_for_level(current_user.assessment_level)
    query = db.query(Mission).filter(
        Mission.is_active.is_(True),
        Mission.difficulty >= lo,
        Mission.difficulty <= hi,
    )
    candidates = [m for m in query.all() if str(m.mission_id) not in done_today]

    if current_user.is_demo:
        wow = _deterministic_order([m for m in candidates if m.is_wow], current_user.user_id)
        rest = _deterministic_order([m for m in candidates if not m.is_wow], current_user.user_id)
        ordered = wow + rest
    else:
        ordered = _deterministic_order(candidates, current_user.user_id)

    data = [_serialize_mission(m) for m in ordered[:limit]]
    return {"status": "success", "data": data}


@router.get(
    "/history",
    summary="미션 완료 이력 조회",
    description="유저의 미션 인증 시도 이력을 최신순으로 반환합니다. `date`를 넘기면 해당 날짜(YYYY-MM-DD)에 완료된 건만 필터링합니다.",
)
def get_mission_history(
    date: str | None = Query(None, description="YYYY-MM-DD 형식. 넘기면 해당 날짜 완료 건만 필터링"),
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
            "mission_id": str(c.mission_id),
            "mission_title": c.mission.title if c.mission else None,
            "status": c.status,
            "xp_earned": c.xp_earned,
            "token_earned": c.token_earned,
            "completed_at": c.completed_at,
        }
        for c in completions
    ]

    return {"status": "success", "data": data}


@router.get(
    "/{mission_id}",
    summary="미션 상세 조회",
    description="미션의 상세 설명·인증 조건 체크리스트·보상 정보를 반환합니다. (세션 인증 필요)",
)
def get_mission_detail(
    mission_id: str,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    mission = db.get(Mission, mission_id)
    if mission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="미션을 찾을 수 없습니다")

    difficulty_labels = {1: "최하", 2: "하", 3: "중하", 4: "중", 5: "중상", 6: "상", 7: "최상"}

    return {
        "status": "success",
        "data": {
            "mission_id": str(mission.mission_id),
            "title": mission.title,
            "description": mission.description,
            "detail_description": mission.detail_description,
            "difficulty": mission.difficulty,
            "difficulty_label": difficulty_labels.get(mission.difficulty, "-"),
            "category": mission.category,
            "verification_type": mission.verification_type,
            "conditions": mission.conditions or [],
            "xp_reward": mission.xp_reward,
            "token_reward": mission.token_reward,
            "bonus_token": mission.bonus_token,
        },
    }


@router.post(
    "/{mission_id}/submit",
    summary="미션 인증 사진 제출",
    description=(
        "미션 수행 인증 사진을 업로드하고 AI(GPT-4o-mini Vision)로 판별합니다. "
        "`multipart/form-data`로 사진 파일과 촬영 시각을 함께 보내주세요.\n\n"
        "**처리 흐름**: 사진을 S3에 업로드 → AI 판별 → 통과 시 `mission_completions.status='approved'`로 저장하고 "
        "XP(`xp_reward`)와 토큰(`token_reward`+`bonus_token`)을 즉시 적립 + `token_transactions`에 이력 기록. "
        "캐릭터는 미션 승인 1건당 XP 임계값과 무관하게 무조건 1레벨 올라갑니다(MAX_LEVEL=4에서 정지) — "
        "행사 현장 참여자를 포함한 전체 유저 공통 규칙입니다. "
        "실패 시 `status='rejected'`, 보상 지급 없음.\n\n"
        "AI는 실패 판정을 최소화하도록 설계되어 있어(어렵게 외출한 사용자에게 '실패'는 심한 트리거가 됨) "
        "`ai_feedback`은 판정과 무관하게 항상 긍정적인 문구입니다."
    ),
)
async def submit_mission(
    mission_id: str,
    photo: UploadFile = File(..., description="미션 인증 사진 파일 (jpg/png 등 이미지)"),
    taken_at: datetime = Form(..., description="사진 촬영 시각 (ISO 8601)"),
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
    completion.photo_taken_at = taken_at
    completion.ai_verdict = ai_verdict
    completion.ai_feedback = ai_feedback

    token_balance = None
    character_level_before = current_user.character_level
    character_level_after = current_user.character_level
    leveled_up = False
    character_image = None
    next_level_xp = None
    total_token_reward = mission.token_reward + mission.bonus_token

    if ai_verdict:
        completion.status = "approved"
        completion.xp_earned = mission.xp_reward
        completion.token_earned = total_token_reward
        completion.completed_at = datetime.now(timezone.utc)

        wallet = db.get(TokenWallet, current_user.user_id)
        wallet.token_balance += total_token_reward
        db.add(TokenTransaction(
            user_id=current_user.user_id,
            amount=total_token_reward,
            reason="mission_complete",
            ref_id=completion.completion_id,
        ))
        token_balance = wallet.token_balance

        level_result = check_level_up(
            current_user.character_level,
            current_user.character_xp,
            mission.xp_reward,
        )
        current_user.character_level = level_result["new_level"]
        current_user.character_xp = level_result["new_xp"]
        character_level_after = level_result["new_level"]
        leveled_up = level_result["leveled_up"]
        character_image = level_result["character_image"]
        next_level_xp = level_result["next_level_xp"]
    else:
        completion.status = "rejected"

    db.commit()

    return {
        "status": "success",
        "data": {
            "completion_id": str(completion.completion_id),
            "ai_verdict": ai_verdict,
            "ai_feedback": ai_feedback,
            "xp_earned": completion.xp_earned,
            "token_earned": completion.token_earned,
            "bonus_token": mission.bonus_token if ai_verdict else 0,
            "character_level_before": character_level_before,
            "character_level_after": character_level_after,
            "character_xp": current_user.character_xp,
            "leveled_up": leveled_up,
            "character_image": character_image,
            "next_level_xp": next_level_xp,
            "token_balance": token_balance,
        },
    }


@router.get(
    "/{mission_id}/result",
    summary="미션 인증 결과 조회",
    description=(
        "특정 미션의 가장 최근 인증 시도 결과를 조회합니다. "
        "`POST /missions/{mission_id}/submit`은 현재 동기 처리라 즉시 결과가 나오지만, "
        "추후 비동기 처리로 바뀌는 경우를 대비한 폴링용 엔드포인트입니다.\n\n"
        "`photo_url`은 제출 당시 S3에 업로드된 인증 사진 URL을 그대로 반환합니다 "
        "(버킷이 퍼블릭 읽기로 설정되어 있어야 프론트에서 바로 렌더링됩니다)."
    ),
)
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
            "xp_earned": completion.xp_earned,
            "token_earned": completion.token_earned,
            "photo_url": completion.photo_url,
        },
    }
