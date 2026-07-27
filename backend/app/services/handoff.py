"""
Live handoff service: finds staff who are marked online, and notifies them
by email that a visitor wants to talk to a real person.

This is intentionally decoupled from lead_agent.py so it can be reused from
admin routes too (e.g. a "re-notify" button).
"""
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
    """
    agents = get_online_agents(db)
    if not agents:
        return []

    try:
        from app.services.notification import NotificationService
        NotificationService.send_handoff_notification(conversation_id, agents)
    except Exception as e:
        # Don't let an email failure block the handoff flow - the conversation
        # is still marked pending_human and will show up in the admin queue.
        print(f"⚠️ Failed to send handoff notification emails: {e}")

    return agents