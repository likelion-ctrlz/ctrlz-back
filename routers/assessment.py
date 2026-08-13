from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from database import get_db
from dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/assessment", tags=["assessment"])

LEVEL_THRESHOLDS = [7, 14, 21]  # 0~7=레벨1, 8~14=레벨2, 15~21=레벨3, 22+=레벨4

DESCRIPTIONS = {
    1: "전반적으로 안정적인 상태예요. 꾸준히 활동을 이어가봐요.",
    2: "외출 빈도가 낮고 사회적 활동이 제한되어 있어요. 작은 외출 미션부터 시작해봐요.",
    3: "고립·은둔 경향이 뚜렷해요. 부담 없는 미션으로 천천히 시작해봐요.",
    4: "도움이 필요한 상태예요. 전문 프로그램 연계를 함께 살펴봐요.",
}


class AssessmentSubmitRequest(BaseModel):
    answers: list[int]


def _score_to_level(total: int) -> int:
    for level, threshold in enumerate(LEVEL_THRESHOLDS, start=1):
        if total <= threshold:
            return level
    return 4


def _classify_type(answers: list[int]) -> str:
    # TODO: 설문 문항 구성이 확정되면 문항별 카테고리 기준으로 정확히 매핑할 것.
    # 임시로 응답을 절반으로 나눠 앞쪽을 외출 관련, 뒤쪽을 관계 관련 문항으로 가정.
    half = max(len(answers) // 2, 1)
    outing_score = sum(answers[:half])
    relation_score = sum(answers[half:])
    if outing_score > relation_score:
        return "은둔형"
    if relation_score > outing_score:
        return "고립형"
    return "복합형"


@router.post("/submit")
def submit_assessment(
    payload: AssessmentSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    if not payload.answers:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="answers가 비어 있습니다",
        )

    level = _score_to_level(sum(payload.answers))
    user_type = _classify_type(payload.answers)

    current_user.status_level = level
    current_user.user_type = user_type
    db.commit()

    return {
        "status": "success",
        "data": {
            "status_level": level,
            "user_type": user_type,
            "description": DESCRIPTIONS[level],
        },
    }


@router.get("/result")
def get_assessment_result(current_user: User = Depends(get_current_user)):
    if current_user.status_level is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="자가진단 결과가 없습니다")

    return {
        "status": "success",
        "data": {
            "status_level": current_user.status_level,
            "user_type": current_user.user_type,
            "assessed_at": current_user.updated_at,
        },
    }
