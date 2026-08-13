from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from database import get_db
from dependencies import get_current_user
from models.program import Program, ProgramReferral
from models.user import User

router = APIRouter(prefix="/programs", tags=["programs"])


class ProgramApplyRequest(BaseModel):
    status: str = "applied"


@router.get("")
def get_programs(
    region: str | None = None,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    query = db.query(Program).filter(Program.is_active.is_(True))
    target_region = region or current_user.region
    if target_region:
        query = query.filter(Program.region == target_region)

    programs = query.all()

    data = [
        {
            "program_id": str(p.program_id),
            "title": p.title,
            "agency_name": p.agency_name,
            "region": p.region,
            "description": p.description,
            "contact": p.contact,
            "apply_url": p.apply_url,
        }
        for p in programs
    ]

    return {"status": "success", "data": data}


@router.post("/{program_id}/apply")
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
