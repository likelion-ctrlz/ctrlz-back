from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from database import get_db
from dependencies import get_current_user
from models.program import Program, ProgramReferral
from models.user import User
from services.everlearning import fetch_programs

router = APIRouter(prefix="/programs", tags=["programs"])


class ProgramApplyRequest(BaseModel):
    status: str = Field("applied", description="기록할 신청 상태. 기본값 'applied'(신청함)")


@router.get(
    "",
    summary="지역 지원 프로그램·기관 목록 조회",
    description=(
        "유저 지역(또는 쿼리로 넘긴 `region`)에 맞는 지원 프로그램·기관 목록을 반환합니다.\n\n"
        "매칭되는 데이터가 없으면(아직 시딩 전 등) 에버러닝 API로 가져와 `programs`에 실제 레코드로 "
        "저장한 뒤 반환합니다. 이렇게 저장된 항목도 `program_id`가 정식 발급되어 "
        "`POST /{program_id}/apply`로 연계 이력 기록이 가능합니다.\n\n"
        "실제 신청은 이 서비스 밖에서(외부 URL로 이동) 이뤄지므로, 여기서는 조회만 담당합니다."
    ),
)
def get_programs(
    region: str | None = Query(None, description="조회할 지역 (시·구 단위). 생략 시 내 프로필의 region 사용"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    target_region = region or current_user.region

    query = db.query(Program).filter(Program.is_active.is_(True))
    if target_region:
        query = query.filter(Program.region == target_region)

    programs = query.all()

    if not programs:
        fetched = fetch_programs(region=target_region)
        programs = [
            Program(
                title=p["title"],
                agency_name=p["agency_name"],
                region=p["region"] or target_region,
                description=p["description"],
                image_url=p.get("image_url"),
                contact=p["contact"],
                apply_url=p["apply_url"],
                is_active=True,
            )
            for p in fetched
        ]
        db.add_all(programs)
        db.commit()

    data = [
        {
            "program_id": str(p.program_id),
            "title": p.title,
            "agency_name": p.agency_name,
            "region": p.region,
            "description": p.description,
            "image_url": p.image_url,
            "contact": p.contact,
            "apply_url": p.apply_url,
        }
        for p in programs
    ]

    return {"status": "success", "data": data}


@router.post(
    "/{program_id}/apply",
    summary="프로그램 관심·연계 이력 기록",
    description=(
        "실제 신청은 외부 URL(`apply_url`)로 이동해서 처리되므로, "
        "이 엔드포인트는 '신청 의사를 눌렀다'는 이력만 `program_referrals`에 남깁니다."
    ),
)
def apply_program(
    program_id: str,
    payload: ProgramApplyRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    program = db.get(Program, program_id)
    if program is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="프로그램을 찾을 수 없습니다")

    referral = ProgramReferral(
        user_id=current_user.user_id,
        program_id=program.program_id,
        status=payload.status,
    )
    db.add(referral)
    db.commit()

    return {
        "status": "success",
        "data": {"referral_id": str(referral.referral_id), "status": referral.status},
    }
