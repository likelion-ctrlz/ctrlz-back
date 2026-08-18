import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from database import get_db
from dependencies import get_current_user
from models.hobby import HobbyActivity, HobbyParticipation
from models.token import TokenTransaction, TokenWallet
from models.user import User
from services.everlearning import fetch_hobby_courses

router = APIRouter(prefix="/hobbies", tags=["hobbies"])


def _serialize_hobby_card(hobby: HobbyActivity) -> dict:
    """목록 카드 + 상세 페이지 공통으로 쓰는 필드."""
    return {
        "hobby_id": str(hobby.hobby_id),
        "title": hobby.title,
        "description": hobby.description,
        "category": hobby.category,
        "tags": hobby.tags or [],
        "difficulty": hobby.difficulty,
        "image_url": hobby.image_url,
        "token_cost": hobby.token_cost,
    }


@router.get(
    "/recommended",
    summary="추천 취미활동 목록 조회",
    description=(
        "유저의 자가진단 `assessment_level`에 맞는 취미활동을 `hobby_activities` 테이블에서 필터링해 반환합니다.\n\n"
        "매칭되는 데이터가 없으면(아직 시딩 전 등) 공공데이터포털 에버러닝 강좌정보 API로 가져와 "
        "`hobby_activities`에 실제 레코드로 저장한 뒤 반환합니다 (모든 레벨에 매칭되도록 저장). "
        "이렇게 저장된 항목도 `hobby_id`가 정식으로 발급되어 `POST /{hobby_id}/apply`로 신청 가능합니다 "
        "(실제 외부 기관에 신청이 접수되는 건 아니고, 앱 내 토큰 사용 기록용입니다). "
        "API 호출도 실패하면 큐레이션된 더미 데이터로 한 번 더 폴백합니다."
    ),
)
def get_recommended_hobbies(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    query = db.query(HobbyActivity).filter(HobbyActivity.is_active.is_(True))
    if current_user.assessment_level is not None:
        query = query.filter(HobbyActivity.recommended_level.any(current_user.assessment_level))

    hobbies = query.all()

    if not hobbies:
        # DB에 아직 매칭되는 데이터가 없으면 외부 API(자체 폴백 포함)로 가져와 실제로 저장한다.
        # recommended_level을 전체로 걸어 어떤 유저가 조회해도 이후엔 DB에서 바로 찾도록 함.
        fetched = fetch_hobby_courses()
        hobbies = [
            HobbyActivity(
                title=h["title"],
                description=h["description"],
                detail_description=h.get("detail_description"),
                category=h["category"],
                tags=h.get("tags"),
                difficulty=h.get("difficulty", "초급"),
                image_url=h.get("image_url"),
                schedule=h.get("schedule"),
                location=h.get("location"),
                duration=h.get("duration"),
                capacity=h.get("capacity"),
                physical_burden=h.get("physical_burden"),
                social_burden=h.get("social_burden"),
                preparation_burden=h.get("preparation_burden"),
                conditions=h.get("conditions"),
                token_cost=h["token_cost"],
                recommended_level=[1, 2, 3, 4],
                is_active=True,
            )
            for h in fetched
        ]
        db.add_all(hobbies)
        db.commit()

    data = [_serialize_hobby_card(h) for h in hobbies]

    return {"status": "success", "data": data}


@router.get(
    "/{hobby_id}",
    summary="취미활동 상세 조회",
    description="일정·장소·소요시간·정원·부담 수준(신체 활동/사회적 상호작용/사전 준비)·참여 조건 등 상세 페이지에 필요한 정보를 반환합니다.",
)
def get_hobby_detail(
    hobby_id: str,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    hobby = db.get(HobbyActivity, hobby_id)
    if hobby is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="취미활동을 찾을 수 없습니다")

    return {
        "status": "success",
        "data": {
            **_serialize_hobby_card(hobby),
            "detail_description": hobby.detail_description,
            "schedule": hobby.schedule,
            "location": hobby.location,
            "duration": hobby.duration,
            "capacity": hobby.capacity,
            "physical_burden": hobby.physical_burden,
            "social_burden": hobby.social_burden,
            "preparation_burden": hobby.preparation_burden,
            "conditions": hobby.conditions or [],
        },
    }


@router.post(
    "/{hobby_id}/apply",
    summary="취미활동 참여 신청",
    description=(
        "보유 토큰으로 취미활동 참여를 신청합니다. "
        "잔액이 `token_cost`보다 적으면 400 에러를 반환합니다.\n\n"
        "신청과 동시에 `token_wallets.token_balance`가 즉시 차감되고 `token_transactions`에 "
        "`reason='hobby_apply'`, 음수 `amount`로 이력이 남습니다."
    ),
)
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
