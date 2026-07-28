"""
Live handoff service: finds staff who are marked online, and notifies them
by email that a visitor wants to talk to a real person.

This is intentionally decoupled from lead_agent.py so it can be reused from
admin routes too (e.g. a "re-notify" button).
"""
import threading
from types import SimpleNamespace
from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import STAFF_ROLES, User


def get_online_agents(db: Session) -> List[User]:
    """Return all active staff members who have marked themselves online."""
    return (
        db.query(User)
        .filter(
            User.is_online.is_(True),
            User.is_active.is_(True),
            User.role.in_(STAFF_ROLES),
        )
        .all()
    )


def notify_available_agents(db: Session, conversation_id: UUID) -> List[User]:
    """
    Find online staff and email them a link to claim this live chat.
    Returns the list of agents that were notified (empty list = nobody online).

    NOTE: the actual emails are sent on a background thread. Sending them
    inline here was the main cause of "the chatbot is slow" - this function
    used to email EVERY online agent one at a time (a full SMTP handshake
    each) before the visitor's "connecting you now" reply could even be
    returned. Now the online-agent lookup (fast, just a DB query) still
    happens immediately so the bot's reply wording is correct, but the
    slow part (actually sending mail) no longer blocks the visitor.
    """
    agents = get_online_agents(db)
    if not agents:
        return []

    # Snapshot plain values now, while the DB session is still open - the
    # background thread must not touch these ORM objects after this
    # request's session closes.
    agent_snapshots = [
        SimpleNamespace(
            email=a.email,
            first_name=getattr(a, "first_name", None),
            full_name=getattr(a, "full_name", None),
        )
        for a in agents
    ]

    def _send_handoff_emails_in_background(snapshots=agent_snapshots):
        try:
            from app.services.notification import NotificationService
            NotificationService.send_handoff_notification(conversation_id, snapshots)
        except Exception as e:
            # Don't let an email failure block the handoff flow - the conversation
            # is still marked pending_human and will show up in the admin queue.
            print(f"⚠️ Failed to send handoff notification emails: {e}")

    threading.Thread(target=_send_handoff_emails_in_background, daemon=True).start()

    return agents