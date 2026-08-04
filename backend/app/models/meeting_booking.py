from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class MeetingBooking(Base):
    __tablename__ = "meeting_bookings"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String(50), nullable=False, index=True)

    visitor_name = Column(String(255), nullable=False)
    visitor_email = Column(String(255), nullable=False, index=True)
    visitor_timezone = Column(
        String(64),
        nullable=False,
        default="Asia/Karachi",
    )
    meeting_purpose = Column(Text, nullable=False)

    calendar_id = Column(
        String(255),
        nullable=False,
        default="incdatamart@gmail.com",
    )

    start_time_utc = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    end_time_utc = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    status = Column(
        String(32),
        nullable=False,
        default="confirmed",
        index=True,
    )

    google_event_id = Column(String(255), nullable=True, unique=True)
    google_meet_link = Column(String(500), nullable=True)

    confirmation_sent_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    reminder_sent_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
