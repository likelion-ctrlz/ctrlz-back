from datetime import date as date_cls

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from database import get_db
from dependencies import get_current_user
from models.mission import MissionCompletion
from models.report import DailyReport
from models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily")
def get_daily_report(
    date: str | None = None,
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
