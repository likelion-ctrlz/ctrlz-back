from datetime import date as date_cls

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DBSession

from database import get_db
from dependencies import get_current_user
from models.mission import MissionCompletion
from models.report import DailyReport
from models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/daily",
    summary="일일 리포트 조회",
    description=(
        "해당 날짜의 미션 수행 요약(완료 개수, 획득 토큰, 미션명 목록)과 AI 리포트 문구를 반환합니다.\n\n"
        "이미 생성된 리포트가 있으면 그대로 반환하고, 없으면 그날 완료된 미션들을 집계해 새로 생성·저장합니다 "
        "(하루에 한 번만 생성되고 이후엔 캐시처럼 재사용됨). "
        "현재 `ai_report_text`는 AI가 아니라 템플릿 문자열로 생성됩니다."
    ),
)
def get_daily_report(
    date: str | None = Query(None, description="YYYY-MM-DD. 생략 시 오늘 날짜"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    target_date = date_cls.fromisoformat(date) if date else date_cls.today()

    report = (
        db.query(DailyReport)
        .filter(DailyReport.user_id == current_user.user_id, DailyReport.date == target_date)
        .first()
    )

    if report is None:
        completions = (
            db.query(MissionCompletion)
            .filter(
                MissionCompletion.user_id == current_user.user_id,
                MissionCompletion.status == "approved",
            )
            .all()
        )
        completions = [c for c in completions if c.completed_at and c.completed_at.date() == target_date]

        mission_summary = {
            "completed": len(completions),
            "tokens_earned": sum(c.token_earned for c in completions),
            "missions": [c.mission.title for c in completions if c.mission],
        }
        # TODO: AI 연동 필요 — 현재는 템플릿 문자열로 대체
        ai_report_text = (
            f"오늘 {mission_summary['completed']}개의 미션을 완료하고 "
            f"{mission_summary['tokens_earned']}토큰을 모았어요."
        )

        report = DailyReport(
            user_id=current_user.user_id,
            date=target_date,
            mission_summary=mission_summary,
            ai_report_text=ai_report_text,
        )
        db.add(report)
        db.commit()

    return {
        "status": "success",
        "data": {
            "date": report.date.isoformat(),
            "mission_summary": report.mission_summary,
            "ai_report_text": report.ai_report_text,
        },
    }
