import os
import secrets

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.meeting_reminder_service import (
    send_due_meeting_reminders,
)


router = APIRouter(
    prefix="/cron",
    tags=["Meeting reminders"],
)


@router.get("/meeting-reminders")
def meeting_reminders(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    cron_secret = os.getenv("CRON_SECRET")

    if not cron_secret:
        raise HTTPException(
            status_code=503,
            detail="CRON_SECRET is not configured",
        )

    expected_header = f"Bearer {cron_secret}"

    if not authorization or not secrets.compare_digest(
        authorization,
        expected_header,
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
        )

    return send_due_meeting_reminders(db)
