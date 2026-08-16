from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from database import get_db
from dependencies import get_current_user
from models.user import User
from services.assessment import calculate_assessment

router = APIRouter(prefix="/assessment", tags=["assessment"])

# 문항 순서: [1.외출빈도, 2.두문불출, 3.지속기간, 4.오프라인접촉, 5.관계형태, 6.지지체계, 7.소속여부, 8.정서상태]
QUESTION_COUNT = 8

DESCRIPTIONS = {
    1: "외출과 사회적 교류가 많이 위축되어 있어요. 작은 미션부터 천천히 시작해봐요.",
    2: "외출 빈도가 낮고 사회적 활동이 제한되어 있어요. 작은 외출 미션부터 시작해봐요.",
    3: "고립·은둔 경향이 나타나기 시작했어요. 꾸준한 루틴을 만들어가봐요.",
    4: "전반적으로 안정적인 상태예요. 꾸준히 활동을 이어가봐요.",
}


class AssessmentSubmitRequest(BaseModel):
    answers: list[int] = Field(
        description=(
            "8문항 응답 점수를 순서대로 담은 배열. "
            "[1.외출빈도, 2.두문불출, 3.지속기간, 4.오프라인접촉, 5.관계형태, 6.지지체계, 7.소속여부, 8.정서상태] "
            "순서를 반드시 지켜야 합니다. "
            "Q1(0~4), Q2(0~3), Q3(0~4), Q4(0~4), Q5(0~3), Q6(0~3), Q7(0~3), Q8(0~3)."
        ),
        examples=[[3, 2, 2, 3, 2, 2, 2, 1]],
    )


@router.post(
    "/submit",
    summary="자가진단 설문 제출",
    description=(
        "8문항 응답을 받아 은둔축·고립축·심각도축 3개 축으로 위험 수준(레벨 1~4)과 "
        "유형(관찰군/은둔형/고립형/복합형)을 산출하고 `users` 테이블에 저장합니다. 재제출 시 이전 결과를 덮어씁니다.\n\n"
        "**1단계 스크리닝 게이트**: 은둔축+고립축 합산 점수가 만점(21점)의 42% 미만이면 무조건 관찰군(레벨 4)으로 분류하고 종료합니다.\n\n"
        "**2단계 유형 판정**: 은둔축 비율 42% 이상이면서 Q3(지속기간) ≥ 2(6개월 이상)면 은둔형, "
        "고립축 비율 42% 이상이면 고립형, 둘 다 해당하면 복합형입니다.\n\n"
        "**3단계 레벨 산정**: 3축 평균(overall_pct) 75%↑ Lv.1(가장 심각) / 50%↑ Lv.2 / 25%↑ Lv.3 / 그 미만 Lv.4. "
        "관찰군은 무조건 레벨 4."
    ),
)
def submit_assessment(
    payload: AssessmentSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    if len(payload.answers) != QUESTION_COUNT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"answers는 {QUESTION_COUNT}개 문항 응답이어야 합니다",
        )

    result = calculate_assessment(payload.answers)

    current_user.assessment_level = result["assessment_level"]
    current_user.assessment_type = result["assessment_type"]
    current_user.assessment_score = result["assessment_score"]
    current_user.assessed_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "status": "success",
        "data": {
            **result,
            "description": DESCRIPTIONS[result["assessment_level"]],
        },
    }


@router.get(
    "/result",
    summary="가장 최근 자가진단 결과 조회",
    description="가장 최근 제출한 자가진단 결과(레벨, 유형, 점수)를 조회합니다. 아직 한 번도 제출하지 않았다면 404를 반환합니다.",
)
def get_assessment_result(current_user: User = Depends(get_current_user)):
    if current_user.assessment_level is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="자가진단 결과가 없습니다")

    return {
        "status": "success",
        "data": {
            "assessment_level": current_user.assessment_level,
            "assessment_type": current_user.assessment_type,
            "assessment_score": current_user.assessment_score,
            "assessed_at": current_user.assessed_at,
        },
    }
