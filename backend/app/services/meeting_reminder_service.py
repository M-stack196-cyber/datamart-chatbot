import html
import os
import smtplib
from datetime import datetime, time, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.models.meeting_booking import MeetingBooking


COMPANY_TIMEZONE = ZoneInfo(
    os.getenv("GOOGLE_CALENDAR_TIMEZONE", "Asia/Karachi")
)


def _visitor_timezone(value: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(value or "Asia/Karachi")
    except ZoneInfoNotFoundError:
        return COMPANY_TIMEZONE


def _send_reminder_email(
    booking: MeetingBooking,
) -> None:
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_user or not smtp_password:
        raise RuntimeError(
            "SMTP credentials are not configured"
        )

    if not booking.google_meet_link:
        raise RuntimeError(
            "Google Meet link is missing"
        )

    visitor_zone = _visitor_timezone(
        booking.visitor_timezone
    )

    start_utc = booking.start_time_utc

    if start_utc.tzinfo is None:
        start_utc = start_utc.replace(
            tzinfo=timezone.utc
        )

    start_local = start_utc.astimezone(visitor_zone)

    visitor_name = html.escape(booking.visitor_name)
    purpose = html.escape(booking.meeting_purpose)
    meet_link = html.escape(booking.google_meet_link)
    timezone_name = html.escape(
        booking.visitor_timezone
        or "Asia/Karachi"
    )

    subject = (
        "Reminder: Your Datamart meeting is today at "
        + start_local.strftime("%I:%M %p")
    )

    plain_body = f"""Hello {booking.visitor_name},

This is a reminder that your Datamart meeting is scheduled for today.

Date: {start_local.strftime("%A, %B %d, %Y")}
Time: {start_local.strftime("%I:%M %p")} ({booking.visitor_timezone})
Duration: 30 minutes
Purpose: {booking.meeting_purpose}

Join Google Meet:
{booking.google_meet_link}

Please join a few minutes before the scheduled time.

Best regards,
Datamart Team
"""

    html_body = f"""
    <html>
      <body style="font-family:Arial,sans-serif;color:#1f2937;line-height:1.6">
        <div style="max-width:600px;margin:auto;padding:24px;border:1px solid #e5e7eb;border-radius:12px">
          <h2 style="margin-top:0">Meeting Reminder</h2>

          <p>Hello {visitor_name},</p>

          <p>
            This is a reminder that your Datamart meeting is
            scheduled for today.
          </p>

          <table style="width:100%;border-collapse:collapse;margin:20px 0">
            <tr>
              <td style="padding:7px 0"><strong>Date</strong></td>
              <td style="padding:7px 0">
                {start_local.strftime("%A, %B %d, %Y")}
              </td>
            </tr>
            <tr>
              <td style="padding:7px 0"><strong>Time</strong></td>
              <td style="padding:7px 0">
                {start_local.strftime("%I:%M %p")} ({timezone_name})
              </td>
            </tr>
            <tr>
              <td style="padding:7px 0"><strong>Duration</strong></td>
              <td style="padding:7px 0">30 minutes</td>
            </tr>
            <tr>
              <td style="padding:7px 0"><strong>Purpose</strong></td>
              <td style="padding:7px 0">{purpose}</td>
            </tr>
          </table>

          <p style="margin:28px 0">
            <a
              href="{meet_link}"
              style="background:#111827;color:white;padding:12px 20px;text-decoration:none;border-radius:8px;display:inline-block"
            >
              Join Google Meet
            </a>
          </p>

          <p>Please join a few minutes before the scheduled time.</p>

          <p>
            Best regards,<br>
            Datamart Team
          </p>
        </div>
      </body>
    </html>
    """

    message = MIMEMultipart("alternative")
    message["From"] = smtp_user
    message["To"] = booking.visitor_email
    message["Subject"] = subject

    message.attach(
        MIMEText(plain_body, "plain", "utf-8")
    )
    message.attach(
        MIMEText(html_body, "html", "utf-8")
    )

    with smtplib.SMTP(
        smtp_server,
        smtp_port,
        timeout=30,
    ) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(message)


def send_due_meeting_reminders(
    db: Session,
    now: datetime | None = None,
) -> dict:
    now_utc = now or datetime.now(timezone.utc)

    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(
            tzinfo=timezone.utc
        )

    now_utc = now_utc.astimezone(timezone.utc)
    today_local = now_utc.astimezone(
        COMPANY_TIMEZONE
    ).date()

    day_start_local = datetime.combine(
        today_local,
        time.min,
        COMPANY_TIMEZONE,
    )
    next_day_local = day_start_local + timedelta(days=1)

    day_start_utc = day_start_local.astimezone(
        timezone.utc
    )
    next_day_utc = next_day_local.astimezone(
        timezone.utc
    )

    bookings = (
        db.query(MeetingBooking)
        .filter(
            MeetingBooking.status == "confirmed",
            MeetingBooking.reminder_sent_at.is_(None),
            MeetingBooking.start_time_utc >= day_start_utc,
            MeetingBooking.start_time_utc < next_day_utc,
            MeetingBooking.start_time_utc > now_utc,
        )
        .order_by(MeetingBooking.start_time_utc.asc())
        .all()
    )

    sent = 0
    failed: list[dict] = []

    for booking in bookings:
        try:
            _send_reminder_email(booking)
            booking.reminder_sent_at = datetime.now(
                timezone.utc
            )
            db.add(booking)
            db.commit()
            sent += 1
        except Exception as error:
            db.rollback()
            failed.append(
                {
                    "booking_id": booking.id,
                    "error": str(error),
                }
            )
            print(
                "Meeting reminder error "
                f"for booking {booking.id}: {error}"
            )

    return {
        "success": True,
        "date": today_local.isoformat(),
        "checked": len(bookings),
        "sent": sent,
        "failed": len(failed),
        "failures": failed,
    }
