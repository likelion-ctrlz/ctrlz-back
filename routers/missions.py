from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
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


@router.get(
    "/recommended",
    summary="추천 미션 목록 조회",
    description=(
        "레벨 1(쉬움)~4(어려움) 각 레벨에서 미션을 1개씩 뽑아 난이도 사다리 형태로 총 4개를 반환합니다. "
        "유저의 자가진단 `status_level`로 필터링해서 특정 레벨만 보여주지 않고, "
        "항상 레벨 1~4를 고르게 보여줍니다 (자가진단 미완료 유저도 동일하게 조회 가능).\n\n"
        "AI 기반 추천이 아니라 DB 필터링을 사용합니다 (재현성·난이도 곡선 안정성을 위해 의도된 설계)."
    ),
)
def get_recommended_missions(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    data = []
    for level in (1, 2, 3, 4):
        mission = (
            db.query(Mission)
            .filter(Mission.is_active.is_(True), Mission.target_level.any(level))
            .order_by(Mission.created_at)
            .first()
        )
        if mission is None:
            continue

        data.append({
            "mission_id": str(mission.mission_id),
            "title": mission.title,
            "description": mission.description,
            "difficulty": mission.difficulty,
            "category": mission.category,
            "verification_type": mission.verification_type,
            "token_reward": mission.token_reward,
        })

    return {"status": "success", "data": data}


@router.post(
    "/{mission_id}/submit",
    summary="미션 인증 사진 제출",
    description=(
        "미션 수행 인증 사진을 업로드하고 AI(GPT-4o-mini Vision)로 판별합니다. "
        "`multipart/form-data`로 사진 파일과 촬영 GPS·시각을 함께 보내주세요.\n\n"
        "**처리 흐름**: 사진을 S3에 업로드 → AI 판별 → 통과 시 `mission_completions.status='approved'`로 저장하고 "
        "`token_wallets` 잔액을 즉시 `token_reward`만큼 적립 + `token_transactions`에 이력 기록. "
        "실패 시 `status='rejected'`, 토큰 지급 없음.\n\n"
        "AI는 실패 판정을 최소화하도록 설계되어 있어(어렵게 외출한 사용자에게 '실패'는 심한 트리거가 됨) "
        "`ai_feedback`은 판정과 무관하게 항상 긍정적인 문구입니다."
    ),
)
async def submit_mission(
    mission_id: str,
    photo: UploadFile = File(..., description="미션 인증 사진 파일 (jpg/png 등 이미지)"),
    gps_lat: float = Form(..., description="사진 촬영 위치 위도"),
    gps_lng: float = Form(..., description="사진 촬영 위치 경도"),
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


@router.get(
    "/{mission_id}/result",
    summary="미션 인증 결과 조회",
    description=(
        "특정 미션의 가장 최근 인증 시도 결과를 조회합니다. "
        "`POST /missions/{mission_id}/submit`은 현재 동기 처리라 즉시 결과가 나오지만, "
        "추후 비동기 처리로 바뀌는 경우를 대비한 폴링용 엔드포인트입니다."
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
            "token_earned": completion.token_earned,
        },
    }


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
            "mission_title": c.mission.title if c.mission else None,
            "status": c.status,
            "token_earned": c.token_earned,
            "completed_at": c.completed_at,
        }
        for c in completions
    ]

    return {"status": "success", "data": data}
