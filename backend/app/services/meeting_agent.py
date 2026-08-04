import json
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.models.contact_info import ContactInfo
from app.models.conversation_history import ConversationHistory
from app.models.conversation_state import ConversationState
from app.models.meeting_booking import MeetingBooking
from app.services.google_calendar_service import (
    SlotUnavailableError,
    create_google_meeting,
    generate_available_slots,
)


MEETING_STATE_KEY = "__meeting_booking__"

MEETING_PHRASES = (
    "book a meeting",
    "schedule a meeting",
    "schedule meeting",
    "book meeting",
    "schedule a call",
    "book a call",
    "arrange a meeting",
    "arrange a call",
    "set up a meeting",
    "set up a call",
    "have a meeting",
    "do a meeting",
    "meeting with your team",
    "meeting with company",
    "meet with your team",
    "meet your employee",
    "available meeting slots",
    "available slots",
    "book an appointment",
    "schedule an appointment",
)

CANCEL_PHRASES = (
    "cancel",
    "cancel meeting",
    "cancel meeting request",
    "stop",
    "never mind",
    "nevermind",
)

CONFIRM_PHRASES = (
    "yes",
    "yes confirm",
    "yes, confirm",
    "yes, confirm meeting",
    "confirm",
    "confirm meeting",
    "yes confirm meeting",
    "1",
)

CHANGE_SLOT_PHRASES = (
    "no",
    "choose another",
    "another slot",
    "change slot",
    "select another slot",
    "2",
)

TIMEZONE_ALIASES = {
    "pakistan": "Asia/Karachi",
    "lahore": "Asia/Karachi",
    "karachi": "Asia/Karachi",
    "pkt": "Asia/Karachi",
    "pakistan time": "Asia/Karachi",
    "asia/karachi": "Asia/Karachi",
    "utc": "UTC",
    "gmt": "UTC",
    "uk": "Europe/London",
    "london": "Europe/London",
    "uae": "Asia/Dubai",
    "dubai": "Asia/Dubai",
    "est": "America/New_York",
    "new york": "America/New_York",
    "cst": "America/Chicago",
    "chicago": "America/Chicago",
    "mst": "America/Denver",
    "denver": "America/Denver",
    "pst": "America/Los_Angeles",
    "los angeles": "America/Los_Angeles",
}


class MeetingBookingAgent:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def is_meeting_request(message: str) -> bool:
        message_lower = message.lower().strip()
        return any(
            phrase in message_lower
            for phrase in MEETING_PHRASES
        )

    @staticmethod
    def _valid_name(value: str) -> bool:
        words = value.strip().split()

        if not 2 <= len(words) <= 5:
            return False

        return all(
            re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", word)
            for word in words
        )

    @staticmethod
    def _extract_email(value: str) -> str | None:
        match = re.search(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            value,
        )
        return match.group(0).lower() if match else None

    @staticmethod
    def _parse_timezone(value: str) -> str | None:
        cleaned = value.strip()
        alias = TIMEZONE_ALIASES.get(cleaned.lower())

        if alias:
            return alias

        try:
            ZoneInfo(cleaned)
            return cleaned
        except ZoneInfoNotFoundError:
            return None

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).astimezone(timezone.utc)

    def _load_state(
        self,
        conversation_id: str,
    ) -> tuple[ConversationState, dict]:
        state = (
            self.db.query(ConversationState)
            .filter_by(conversation_id=conversation_id)
            .first()
        )

        if not state:
            state = ConversationState(
                conversation_id=conversation_id,
                mode="bot",
            )
            self.db.add(state)
            self.db.flush()

        try:
            data = json.loads(state.collected_data or "{}")
        except (TypeError, json.JSONDecodeError):
            data = {}

        return state, data

    def _save_state(
        self,
        state: ConversationState,
        data: dict,
    ) -> None:
        state.collected_data = json.dumps(data)
        self.db.add(state)
        self.db.commit()

    def _ensure_contact(
        self,
        conversation_id: str,
    ) -> ContactInfo:
        contact = (
            self.db.query(ContactInfo)
            .filter_by(conversation_id=conversation_id)
            .first()
        )

        if contact:
            return contact

        contact = ContactInfo(
            conversation_id=conversation_id,
            name="Pending",
            email="pending@example.com",
            phone="",
            project_description="Meeting request",
            source="public_widget",
            status="new",
            lead_score=0,
        )

        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def _save_message(
        self,
        conversation_id: str,
        role: str,
        message: str,
    ) -> None:
        self.db.add(
            ConversationHistory(
                conversation_id=conversation_id,
                role=role,
                message=message,
            )
        )
        self.db.commit()

    @staticmethod
    def _format_slots(
        slots: list[dict],
        visitor_timezone: str,
    ) -> str:
        zone = ZoneInfo(visitor_timezone)

        lines = [
            "Here are the next available meeting slots:",
            "",
        ]

        for slot in slots:
            start = MeetingBookingAgent._parse_datetime(
                slot["start_utc"]
            ).astimezone(zone)

            lines.append(
                f'{slot["number"]}. '
                f'{start.strftime("%A, %B %d, %Y at %I:%M %p")} '
                f"({visitor_timezone})"
            )

        lines.extend(
            [
                "",
                "Please select a slot number from 1 to "
                f"{len(slots)}.",
            ]
        )

        return "\n".join(lines)

    @staticmethod
    def _confirmation_message(
        meeting: dict,
        selected_slot: dict,
    ) -> str:
        visitor_zone = ZoneInfo(
            meeting["visitor_timezone"]
        )

        start = MeetingBookingAgent._parse_datetime(
            selected_slot["start_utc"]
        ).astimezone(visitor_zone)

        return "\n".join(
            [
                "Please confirm your meeting details:",
                "",
                f'Name: {meeting["visitor_name"]}',
                f'Email: {meeting["visitor_email"]}',
                (
                    "Date: "
                    + start.strftime("%A, %B %d, %Y")
                ),
                (
                    "Time: "
                    + start.strftime("%I:%M %p")
                    + f' ({meeting["visitor_timezone"]})'
                ),
                "Duration: 30 minutes",
                "Meeting with: Datamart Team",
                f'Purpose: {meeting["meeting_purpose"]}',
                "",
                "1. Yes, confirm meeting",
                "2. No, choose another slot",
                "3. Cancel meeting request",
            ]
        )

    def _next_contact_prompt(
        self,
        meeting: dict,
        contact: ContactInfo,
    ) -> str:
        valid_contact_name = (
            contact.name
            and contact.name.lower() != "pending"
            and self._valid_name(contact.name)
        )

        valid_contact_email = (
            contact.email
            and contact.email.lower()
            != "pending@example.com"
            and self._extract_email(contact.email)
        )

        if valid_contact_name:
            meeting["visitor_name"] = contact.name

        if valid_contact_email:
            meeting["visitor_email"] = contact.email

        if not meeting.get("visitor_name"):
            meeting["phase"] = "collecting_name"
            return "Before booking, what is your full name?"

        if not meeting.get("visitor_email"):
            meeting["phase"] = "collecting_email"
            return "Thanks! What is your email address?"

        meeting["phase"] = "collecting_timezone"
        return (
            "What timezone should I use for showing the meeting slots?\n"
            "For example: Pakistan, Asia/Karachi, New York, "
            "London, Dubai, or UTC."
        )

    def process_message(
        self,
        conversation_id: str,
        message: str,
    ) -> tuple[str | None, bool]:
        state, state_data = self._load_state(
            conversation_id
        )
        meeting = state_data.get(MEETING_STATE_KEY)

        if not meeting and not self.is_meeting_request(message):
            return None, False

        contact = self._ensure_contact(conversation_id)
        self._save_message(
            conversation_id,
            "user",
            message,
        )

        message_clean = message.strip()
        message_lower = message_clean.lower()

        if meeting and message_lower in CANCEL_PHRASES:
            state_data.pop(MEETING_STATE_KEY, None)
            response = (
                "Your meeting request has been cancelled. "
                "No Calendar event or email was created."
            )
            self._save_message(
                conversation_id,
                "assistant",
                response,
            )
            self._save_state(state, state_data)
            return response, True

        if not meeting:
            meeting = {
                "phase": "started",
                "visitor_name": None,
                "visitor_email": None,
                "visitor_timezone": None,
                "meeting_purpose": None,
                "slots": [],
                "selected_slot": None,
            }

            response = self._next_contact_prompt(
                meeting,
                contact,
            )

            state_data[MEETING_STATE_KEY] = meeting
            self._save_message(
                conversation_id,
                "assistant",
                response,
            )
            self._save_state(state, state_data)
            return response, True

        phase = meeting.get("phase")

        if phase == "collecting_name":
            if not self._valid_name(message_clean):
                response = (
                    "Please enter your full name using 2 to 5 words. "
                    "For example: M Tayyab Aslam."
                )
            else:
                meeting["visitor_name"] = message_clean
                contact.name = message_clean
                meeting["phase"] = "collecting_email"
                response = "Thanks! What is your email address?"

        elif phase == "collecting_email":
            email = self._extract_email(message_clean)

            if not email:
                response = (
                    "Please enter a valid email address. "
                    "For example: name@example.com"
                )
            else:
                meeting["visitor_email"] = email
                contact.email = email
                meeting["phase"] = "collecting_timezone"
                response = (
                    "What timezone should I use for showing the "
                    "meeting slots?\n"
                    "For example: Pakistan, Asia/Karachi, New York, "
                    "London, Dubai, or UTC."
                )

        elif phase == "collecting_timezone":
            visitor_timezone = self._parse_timezone(
                message_clean
            )

            if not visitor_timezone:
                response = (
                    "I could not recognize that timezone. "
                    "Please enter Pakistan, Asia/Karachi, New York, "
                    "London, Dubai, UTC, or another valid timezone."
                )
            else:
                meeting["visitor_timezone"] = visitor_timezone
                meeting["phase"] = "collecting_purpose"
                response = (
                    "What would you like to discuss in the meeting?"
                )

        elif phase == "collecting_purpose":
            if len(message_clean) < 3:
                response = (
                    "Please briefly describe the purpose "
                    "of the meeting."
                )
            else:
                meeting["meeting_purpose"] = message_clean

                try:
                    slots = generate_available_slots()
                except Exception as error:
                    response = (
                        "I could not check the Calendar right now. "
                        "Please try again shortly."
                    )
                    print(
                        "Google Calendar slot error:",
                        error,
                    )
                else:
                    meeting["slots"] = slots
                    meeting["phase"] = "selecting_slot"

                    if not slots:
                        response = (
                            "There are no available meeting slots "
                            "during the next 14 days."
                        )
                    else:
                        response = self._format_slots(
                            slots,
                            meeting["visitor_timezone"],
                        )

        elif phase == "selecting_slot":
            try:
                selected_number = int(message_clean)
            except ValueError:
                selected_number = -1

            slots = meeting.get("slots", [])

            selected_slot = next(
                (
                    slot
                    for slot in slots
                    if slot["number"] == selected_number
                ),
                None,
            )

            if not selected_slot:
                response = (
                    "Please select a valid slot number from 1 to "
                    f"{len(slots)}."
                )
            else:
                meeting["selected_slot"] = selected_slot
                meeting["phase"] = "confirming"
                response = self._confirmation_message(
                    meeting,
                    selected_slot,
                )

        elif phase == "confirming":
            if message_lower in CHANGE_SLOT_PHRASES:
                try:
                    slots = generate_available_slots()
                except Exception as error:
                    response = (
                        "I could not refresh the available slots. "
                        "Please try again shortly."
                    )
                    print(
                        "Google Calendar refresh error:",
                        error,
                    )
                else:
                    meeting["slots"] = slots
                    meeting["selected_slot"] = None
                    meeting["phase"] = "selecting_slot"
                    response = self._format_slots(
                        slots,
                        meeting["visitor_timezone"],
                    )

            elif message_lower in CANCEL_PHRASES or message_lower == "3":
                state_data.pop(MEETING_STATE_KEY, None)
                response = (
                    "Your meeting request has been cancelled. "
                    "No Calendar event or email was created."
                )

            elif message_lower in CONFIRM_PHRASES:
                selected_slot = meeting.get(
                    "selected_slot"
                )

                if not selected_slot:
                    meeting["phase"] = "collecting_purpose"
                    response = (
                        "The selected slot is missing. "
                        "Please tell me the meeting purpose again."
                    )
                else:
                    start_utc = self._parse_datetime(
                        selected_slot["start_utc"]
                    )
                    end_utc = self._parse_datetime(
                        selected_slot["end_utc"]
                    )

                    try:
                        google_result = create_google_meeting(
                            visitor_name=meeting[
                                "visitor_name"
                            ],
                            visitor_email=meeting[
                                "visitor_email"
                            ],
                            meeting_purpose=meeting[
                                "meeting_purpose"
                            ],
                            start_utc=start_utc,
                            end_utc=end_utc,
                        )
                    except SlotUnavailableError:
                        slots = generate_available_slots()
                        meeting["slots"] = slots
                        meeting["selected_slot"] = None
                        meeting["phase"] = "selecting_slot"
                        response = (
                            "Sorry, that slot was just booked by "
                            "someone else.\n\n"
                            + self._format_slots(
                                slots,
                                meeting[
                                    "visitor_timezone"
                                ],
                            )
                        )
                    except Exception as error:
                        self.db.rollback()
                        response = (
                            "The meeting could not be created right "
                            "now. Please try confirming again."
                        )
                        print(
                            "Google Calendar booking error:",
                            error,
                        )
                    else:
                        booking = MeetingBooking(
                            conversation_id=conversation_id,
                            visitor_name=meeting[
                                "visitor_name"
                            ],
                            visitor_email=meeting[
                                "visitor_email"
                            ],
                            visitor_timezone=meeting[
                                "visitor_timezone"
                            ],
                            meeting_purpose=meeting[
                                "meeting_purpose"
                            ],
                            calendar_id=(
                                "incdatamart@gmail.com"
                            ),
                            start_time_utc=start_utc,
                            end_time_utc=end_utc,
                            status="confirmed",
                            google_event_id=google_result[
                                "google_event_id"
                            ],
                            google_meet_link=google_result[
                                "google_meet_link"
                            ],
                            confirmation_sent_at=(
                                datetime.now(timezone.utc)
                            ),
                        )

                        contact.name = meeting[
                            "visitor_name"
                        ]
                        contact.email = meeting[
                            "visitor_email"
                        ]
                        contact.project_description = (
                            meeting["meeting_purpose"]
                        )

                        self.db.add(contact)
                        self.db.add(booking)
                        self.db.commit()
                        self.db.refresh(booking)

                        visitor_zone = ZoneInfo(
                            meeting["visitor_timezone"]
                        )
                        start_local = start_utc.astimezone(
                            visitor_zone
                        )

                        meet_link = (
                            google_result[
                                "google_meet_link"
                            ]
                            or "Google Meet link pending"
                        )

                        response = "\n".join(
                            [
                                "✅ Your meeting has been confirmed.",
                                "",
                                (
                                    "Date: "
                                    + start_local.strftime(
                                        "%A, %B %d, %Y"
                                    )
                                ),
                                (
                                    "Time: "
                                    + start_local.strftime(
                                        "%I:%M %p"
                                    )
                                    + " "
                                    + meeting[
                                        "visitor_timezone"
                                    ]
                                ),
                                "Duration: 30 minutes",
                                (
                                    "Purpose: "
                                    + meeting[
                                        "meeting_purpose"
                                    ]
                                ),
                                "",
                                "Google Meet:",
                                meet_link,
                                "",
                                (
                                    "A Google Calendar invitation "
                                    "has been sent to "
                                    + meeting["visitor_email"]
                                    + "."
                                ),
                            ]
                        )

                        state_data.pop(
                            MEETING_STATE_KEY,
                            None,
                        )
            else:
                response = (
                    "Please choose one option:\n"
                    "1. Yes, confirm meeting\n"
                    "2. No, choose another slot\n"
                    "3. Cancel meeting request"
                )

        else:
            state_data.pop(MEETING_STATE_KEY, None)
            response = (
                "The meeting flow was reset. "
                "Please say: I want to schedule a meeting."
            )

        if MEETING_STATE_KEY in state_data:
            state_data[MEETING_STATE_KEY] = meeting

        self.db.add(contact)
        self._save_message(
            conversation_id,
            "assistant",
            response,
        )
        self._save_state(state, state_data)

        return response, True
