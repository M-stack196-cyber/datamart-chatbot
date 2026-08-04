import os
import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.events.freebusy",
]

COMPANY_TIMEZONE = ZoneInfo(
    os.getenv("GOOGLE_CALENDAR_TIMEZONE", "Asia/Karachi")
)
CALENDAR_ID = os.getenv(
    "GOOGLE_CALENDAR_ID",
    "incdatamart@gmail.com",
)

WORK_START = time(11, 0)
WORK_END = time(20, 0)
MEETING_DURATION = timedelta(minutes=30)
MEETING_BUFFER = timedelta(minutes=15)
MINIMUM_NOTICE = timedelta(hours=2)
BOOKING_WINDOW = timedelta(days=14)
MAXIMUM_SLOTS = 8
SLOT_STEP = timedelta(minutes=15)


class GoogleCalendarConfigurationError(RuntimeError):
    pass


class SlotUnavailableError(RuntimeError):
    pass


def _credentials() -> Credentials:
    required = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN"),
    }

    missing = [
        key
        for key, value in required.items()
        if not value
    ]

    if missing:
        raise GoogleCalendarConfigurationError(
            "Missing Google Calendar settings: "
            + ", ".join(missing)
        )

    return Credentials(
        token=None,
        refresh_token=required["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=required["client_id"],
        client_secret=required["client_secret"],
        scopes=CALENDAR_SCOPES,
    )


def calendar_service():
    return build(
        "calendar",
        "v3",
        credentials=_credentials(),
        cache_discovery=False,
    )


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _rfc3339(value: datetime) -> str:
    return (
        _utc_datetime(value)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _parse_google_datetime(value: str) -> datetime:
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).astimezone(timezone.utc)


def _ceil_to_step(value: datetime) -> datetime:
    value = value.replace(second=0, microsecond=0)
    remainder = value.minute % 15

    if remainder:
        value += timedelta(minutes=15 - remainder)

    return value


def get_busy_periods(
    time_min: datetime,
    time_max: datetime,
) -> list[tuple[datetime, datetime]]:
    result = (
        calendar_service()
        .freebusy()
        .query(
            body={
                "timeMin": _rfc3339(time_min),
                "timeMax": _rfc3339(time_max),
                "timeZone": str(COMPANY_TIMEZONE),
                "items": [{"id": CALENDAR_ID}],
            }
        )
        .execute()
    )

    calendar_result = (
        result.get("calendars", {})
        .get(CALENDAR_ID, {})
    )

    errors = calendar_result.get("errors", [])

    if errors:
        raise RuntimeError(
            f"Google Calendar FreeBusy error: {errors}"
        )

    return [
        (
            _parse_google_datetime(period["start"]),
            _parse_google_datetime(period["end"]),
        )
        for period in calendar_result.get("busy", [])
    ]


def _overlaps_busy_period(
    slot_start: datetime,
    slot_end: datetime,
    busy_periods: list[tuple[datetime, datetime]],
) -> bool:
    for busy_start, busy_end in busy_periods:
        protected_start = busy_start - MEETING_BUFFER
        protected_end = busy_end + MEETING_BUFFER

        if (
            slot_start < protected_end
            and slot_end > protected_start
        ):
            return True

    return False


def _slot_display(start_local: datetime) -> str:
    return start_local.strftime(
        "%A, %B %d, %Y at %I:%M %p PKT"
    )


def generate_available_slots(
    now: datetime | None = None,
    maximum_slots: int = MAXIMUM_SLOTS,
) -> list[dict]:
    now_utc = _utc_datetime(
        now or datetime.now(timezone.utc)
    )
    earliest_utc = now_utc + MINIMUM_NOTICE
    latest_utc = now_utc + BOOKING_WINDOW

    busy_periods = get_busy_periods(
        earliest_utc,
        latest_utc,
    )

    earliest_local = earliest_utc.astimezone(
        COMPANY_TIMEZONE
    )
    latest_local = latest_utc.astimezone(
        COMPANY_TIMEZONE
    )

    slots: list[dict] = []
    current_date: date = earliest_local.date()

    while (
        current_date <= latest_local.date()
        and len(slots) < maximum_slots
    ):
        if current_date.weekday() < 5:
            work_start = datetime.combine(
                current_date,
                WORK_START,
                COMPANY_TIMEZONE,
            )
            work_end = datetime.combine(
                current_date,
                WORK_END,
                COMPANY_TIMEZONE,
            )

            candidate = work_start

            if current_date == earliest_local.date():
                candidate = max(
                    candidate,
                    _ceil_to_step(earliest_local),
                )

            while (
                candidate + MEETING_DURATION <= work_end
                and candidate <= latest_local
                and len(slots) < maximum_slots
            ):
                candidate_end = (
                    candidate + MEETING_DURATION
                )

                start_utc = candidate.astimezone(
                    timezone.utc
                )
                end_utc = candidate_end.astimezone(
                    timezone.utc
                )

                if not _overlaps_busy_period(
                    start_utc,
                    end_utc,
                    busy_periods,
                ):
                    slots.append(
                        {
                            "number": len(slots) + 1,
                            "start_utc": _rfc3339(
                                start_utc
                            ),
                            "end_utc": _rfc3339(
                                end_utc
                            ),
                            "start_local": (
                                candidate.isoformat()
                            ),
                            "end_local": (
                                candidate_end.isoformat()
                            ),
                            "display": _slot_display(
                                candidate
                            ),
                            "timezone": (
                                str(COMPANY_TIMEZONE)
                            ),
                        }
                    )

                candidate += SLOT_STEP

        current_date += timedelta(days=1)

    return slots


def validate_slot(
    start_utc: datetime,
    end_utc: datetime,
    now: datetime | None = None,
) -> bool:
    now_utc = _utc_datetime(
        now or datetime.now(timezone.utc)
    )
    start_utc = _utc_datetime(start_utc)
    end_utc = _utc_datetime(end_utc)

    if end_utc - start_utc != MEETING_DURATION:
        return False

    if start_utc < now_utc + MINIMUM_NOTICE:
        return False

    if start_utc > now_utc + BOOKING_WINDOW:
        return False

    start_local = start_utc.astimezone(
        COMPANY_TIMEZONE
    )
    end_local = end_utc.astimezone(
        COMPANY_TIMEZONE
    )

    if start_local.weekday() >= 5:
        return False

    if start_local.date() != end_local.date():
        return False

    if start_local.time() < WORK_START:
        return False

    if end_local.time() > WORK_END:
        return False

    busy_periods = get_busy_periods(
        start_utc - MEETING_BUFFER,
        end_utc + MEETING_BUFFER,
    )

    return not _overlaps_busy_period(
        start_utc,
        end_utc,
        busy_periods,
    )


def create_google_meeting(
    visitor_name: str,
    visitor_email: str,
    meeting_purpose: str,
    start_utc: datetime,
    end_utc: datetime,
) -> dict:
    start_utc = _utc_datetime(start_utc)
    end_utc = _utc_datetime(end_utc)

    if not validate_slot(start_utc, end_utc):
        raise SlotUnavailableError(
            "The selected meeting slot is no longer available"
        )

    request_id = uuid.uuid4().hex

    event_body = {
        "summary": (
            f"Datamart Meeting with {visitor_name}"
        ),
        "description": (
            "Meeting booked through the Datamart chatbot.\n\n"
            f"Purpose: {meeting_purpose}"
        ),
        "start": {
            "dateTime": _rfc3339(start_utc),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": _rfc3339(end_utc),
            "timeZone": "UTC",
        },
        "attendees": [
            {
                "email": visitor_email,
                "displayName": visitor_name,
            }
        ],
        "conferenceData": {
            "createRequest": {
                "requestId": request_id,
                "conferenceSolutionKey": {
                    "type": "hangoutsMeet"
                },
            }
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {
                    "method": "email",
                    "minutes": 1440,
                },
                {
                    "method": "popup",
                    "minutes": 30,
                },
            ],
        },
    }

    event = (
        calendar_service()
        .events()
        .insert(
            calendarId=CALENDAR_ID,
            body=event_body,
            conferenceDataVersion=1,
            sendUpdates="all",
        )
        .execute()
    )

    meet_link = event.get("hangoutLink")

    if not meet_link:
        for entry_point in (
            event.get("conferenceData", {})
            .get("entryPoints", [])
        ):
            if entry_point.get("entryPointType") == "video":
                meet_link = entry_point.get("uri")
                break

    return {
        "google_event_id": event.get("id"),
        "google_meet_link": meet_link,
        "html_link": event.get("htmlLink"),
        "status": event.get("status"),
    }
