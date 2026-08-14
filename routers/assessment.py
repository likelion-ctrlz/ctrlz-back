from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from database import get_db
from dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/assessment", tags=["assessment"])

# 문항 순서: [1.지지체계, 2.사회적빈도, 3.외출빈도, 4.소속여부, 5.변화가능범위]
# 만점 17점 (3+3+4+3+4). 문항별 배점은 피그마 설문 문구 기준.
QUESTION_COUNT = 5

DESCRIPTIONS = {
    1: "전반적으로 안정적인 상태예요. 꾸준히 활동을 이어가봐요.",
    2: "고립·은둔 경향이 나타나기 시작했어요. 작은 외출 미션부터 시작해봐요.",
    3: "고립·은둔 경향이 뚜렷해요. 적극적인 개입이 필요한 상태예요.",
    4: "도움이 필요한 상태예요. 전문 프로그램 연계를 함께 살펴봐요.",
}


class AssessmentSubmitRequest(BaseModel):
    answers: list[int] = Field(
        description=(
            "5문항 응답 점수를 순서대로 담은 배열. "
            "[1.지지체계, 2.사회적빈도, 3.외출빈도, 4.소속여부, 5.변화가능범위] 순서를 반드시 지켜야 합니다. "
            "각 문항의 점수 범위는 문항마다 다릅니다 (0~3 또는 0~4)."
        ),
        examples=[[2, 3, 4, 3, 2]],
    )


def _score_to_level(total: int) -> int:
    if total <= 4:
        return 1
    if total <= 9:
        return 2
    if total <= 13:
        return 3
    return 4


def _classify_type(answers: list[int]) -> str:
    support, frequency, outing, belonging, _change = answers

    # 핵심 위험 점수 = 외출(3) + 사회적빈도(2) + 소속(4), 범위 0~10
    core_risk = outing + frequency + belonging
    if core_risk < 4:
        return "관찰군"

    if outing >= 3 and support >= 2:
        return "복합형"
    if outing >= 3 and support < 2:
        return "은둔형"
    if outing < 3 and support >= 2:
        return "고립형"
    return "고립형" if frequency >= 2 else "관찰군"


@router.post(
    "/submit",
    summary="자가진단 설문 제출",
    description=(
        "5문항 설문 응답을 받아 위험 수준(레벨 1~4)과 유형(관찰군/은둔형/고립형/복합형)을 산출하고 "
        "`users` 테이블에 저장합니다. 재제출 시 이전 결과를 덮어씁니다.\n\n"
        "**레벨**: 5문항 총점(0~17점) 기준 — 0~4점 Lv.1(경미), 5~9점 Lv.2(관심 필요), "
        "10~13점 Lv.3(적극 개입 필요), 14~17점 Lv.4(고위험)\n\n"
        "**유형**: 외출빈도·사회적빈도·소속여부 3문항 합(핵심 위험 점수, 0~10)이 4점 미만이면 "
        "무조건 관찰군. 4점 이상이면 외출빈도·지지체계 점수 조합으로 은둔형/고립형/복합형/관찰군 중 분류합니다."
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


@router.get(
    "/result",
    summary="가장 최근 자가진단 결과 조회",
    description="가장 최근 제출한 자가진단 결과(레벨, 유형)를 조회합니다. 아직 한 번도 제출하지 않았다면 404를 반환합니다.",
)
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
