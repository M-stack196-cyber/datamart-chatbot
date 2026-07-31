import threading
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import STAFF_ROLES, User
from app.models.contact_info import ContactInfo
from app.models.conversation_history import ConversationHistory
from app.models.conversation_state import ConversationState

router = APIRouter(prefix="/admin", tags=["Admin - Live Handoff"])


# ==========================================
# STAFF AVAILABILITY (online/offline toggle)
# ==========================================

class OnlineStatusUpdate(BaseModel):
    is_online: bool


@router.patch("/me/online")
def set_my_online_status(
    payload: OnlineStatusUpdate,
    current_user: User = Depends(require_role(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    """Any staff member (admin/cto/pmo/hr) toggles their own availability
    for live chat handoffs. The chatbot only offers to connect a visitor to
    staff who are currently marked online here."""
    current_user.is_online = payload.is_online
    current_user.last_active_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)
    return {
        "id": current_user.id,
        "name": current_user.display_name,
        "is_online": current_user.is_online,
    }


@router.get("/online-staff")
def list_online_staff(
    _current_user: User = Depends(require_role(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    """See who else on the team is currently online."""
    staff = (
        db.query(User)
        .filter(User.role.in_(STAFF_ROLES), User.is_active.is_(True))
        .order_by(User.is_online.desc(), User.full_name.asc())
        .all()
    )
    return [
        {"id": u.id, "name": u.display_name, "role": u.role, "is_online": u.is_online}
        for u in staff
    ]


# ==========================================
# HANDOFF QUEUE
# ==========================================

@router.get("/handoff/queue")
def get_handoff_queue(
    _current_user: User = Depends(require_role(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    """Conversations currently waiting for a staff member to claim them."""
    pending = (
        db.query(ConversationState)
        .filter(ConversationState.mode == "pending_human")
        .order_by(ConversationState.handoff_requested_at.asc())
        .all()
    )

    results = []
    for state in pending:
        lead = db.query(ContactInfo).filter_by(conversation_id=state.conversation_id).first()
        results.append({
            "conversation_id": str(state.conversation_id),
            "requested_at": state.handoff_requested_at,
            "visitor_name": lead.name if lead and lead.name != "Pending" else "Anonymous visitor",
            "visitor_email": lead.email if lead and lead.email != "pending@example.com" else None,
        })
    return {"queue": results}


@router.get("/handoff/active")
def get_my_active_handoffs(
    current_user: User = Depends(require_role(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    """Conversations this staff member is currently handling live."""
    active = (
        db.query(ConversationState)
        .filter(
            ConversationState.mode == "human",
            ConversationState.assigned_agent_id == current_user.id,
        )
        .order_by(ConversationState.claimed_at.desc())
        .all()
    )
    return {"active": [{"conversation_id": str(s.conversation_id)} for s in active]}


@router.post("/handoff/{conversation_id}/claim")
def claim_handoff(
    conversation_id: str,
    current_user: User = Depends(require_role(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    """Atomically claim a conversation that is waiting for a human.

    The row lock prevents two staff members from successfully claiming the
    same conversation at nearly the same time.
    """
    state = (
        db.query(ConversationState)
        .filter_by(conversation_id=conversation_id)
        .with_for_update()
        .first()
    )

    if not state:
        db.rollback()
        raise HTTPException(404, "Conversation not found")

    # A repeated click by the same employee is harmless.
    if (
        state.mode == "human"
        and state.assigned_agent_id == current_user.id
    ):
        result = {
            "conversation_id": conversation_id,
            "mode": state.mode,
            "assigned_to": current_user.display_name,
            "already_claimed": True,
        }
        db.rollback()
        return result

    if state.mode == "human":
        db.rollback()
        raise HTTPException(
            409,
            "This chat has already been claimed by another team member",
        )

    if (
        state.mode != "pending_human"
        or state.assigned_agent_id is not None
    ):
        db.rollback()
        raise HTTPException(
            409,
            "This conversation is not waiting for a team member",
        )

    state.mode = "human"
    state.assigned_agent_id = current_user.id
    state.claimed_at = datetime.now(timezone.utc)
    state.closed_at = None

    existing_join = (
        db.query(ConversationHistory)
        .filter(
            ConversationHistory.conversation_id
            == conversation_id,
            ConversationHistory.role.in_(
                ["agent", "system"]
            ),
            ConversationHistory.message.contains(
                "joined the chat"
            ),
        )
        .first()
    )

    if not existing_join:
        db.add(
            ConversationHistory(
                conversation_id=conversation_id,
                role="system",
                message=(
                    f"{current_user.display_name} from Datamart "
                    "has joined the chat. How can I help?"
                ),
            )
        )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "conversation_id": conversation_id,
        "mode": state.mode,
        "assigned_to": current_user.display_name,
        "already_claimed": False,
    }


@router.get("/handoff/{conversation_id}/messages")
def get_handoff_messages(
    conversation_id: str,
    current_user: User = Depends(require_role(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    """Return the full transcript while enforcing claimed-chat ownership."""
    state = (
        db.query(ConversationState)
        .filter_by(conversation_id=conversation_id)
        .first()
    )

    if not state:
        raise HTTPException(404, "Conversation not found")

    if (
        state.mode in {"human", "closed"}
        and state.assigned_agent_id is not None
        and state.assigned_agent_id != current_user.id
    ):
        raise HTTPException(
            403,
            "This conversation is assigned to another team member",
        )

    messages = (
        db.query(ConversationHistory)
        .filter(
            ConversationHistory.conversation_id
            == conversation_id
        )
        .order_by(ConversationHistory.id.asc())
        .all()
    )

    return {
        "mode": state.mode,
        "assigned_agent_id": state.assigned_agent_id,
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "message": message.message,
                "created_at": message.created_at,
            }
            for message in messages
        ],
    }


class AgentMessageCreate(BaseModel):
    message: str


@router.post("/handoff/{conversation_id}/message")
def send_handoff_message(
    conversation_id: str,
    payload: AgentMessageCreate,
    current_user: User = Depends(require_role(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    """Save one employee reply for a conversation they have claimed."""
    message_text = payload.message.strip()

    if not message_text:
        raise HTTPException(
            422,
            "Message cannot be empty",
        )

    # Lock the conversation while checking and saving the reply. This makes
    # duplicate prevention reliable even when two requests arrive together.
    state = (
        db.query(ConversationState)
        .filter_by(conversation_id=conversation_id)
        .with_for_update()
        .first()
    )

    if not state:
        db.rollback()
        raise HTTPException(404, "Conversation not found")

    if (
        state.mode != "human"
        or state.assigned_agent_id != current_user.id
    ):
        db.rollback()
        raise HTTPException(
            403,
            "You have not claimed this conversation",
        )

    time_threshold = (
        datetime.now(timezone.utc)
        - timedelta(seconds=5)
    )

    recent_message = (
        db.query(ConversationHistory)
        .filter(
            ConversationHistory.conversation_id
            == conversation_id,
            ConversationHistory.role == "agent",
            ConversationHistory.user_id
            == current_user.id,
            ConversationHistory.message == message_text,
            ConversationHistory.created_at
            >= time_threshold,
        )
        .first()
    )

    if recent_message:
        result = {
            "id": recent_message.id,
            "role": recent_message.role,
            "message": recent_message.message,
            "created_at": recent_message.created_at,
            "duplicate": True,
        }
        db.rollback()
        return result

    message = ConversationHistory(
        conversation_id=conversation_id,
        user_id=current_user.id,
        role="agent",
        message=message_text,
    )
    db.add(message)

    try:
        db.commit()
        db.refresh(message)
    except Exception:
        db.rollback()
        raise

    return {
        "id": message.id,
        "role": message.role,
        "message": message.message,
        "created_at": message.created_at,
        "duplicate": False,
    }


@router.post("/handoff/{conversation_id}/end")
def end_handoff(
    conversation_id: str,
    current_user: User = Depends(require_role(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    """End a claimed live chat exactly once."""
    state = (
        db.query(ConversationState)
        .filter_by(conversation_id=conversation_id)
        .with_for_update()
        .first()
    )

    if not state:
        db.rollback()
        raise HTTPException(404, "Conversation not found")

    if state.assigned_agent_id != current_user.id:
        db.rollback()
        raise HTTPException(
            403,
            "You are not assigned to this conversation",
        )

    # A repeated End click must not create another system message or send
    # another transcript email.
    if state.mode == "closed":
        result = {
            "conversation_id": conversation_id,
            "mode": "closed",
            "already_closed": True,
        }
        db.rollback()
        return result

    if state.mode != "human":
        db.rollback()
        raise HTTPException(
            409,
            "Only an active human conversation can be ended",
        )

    state.mode = "closed"
    state.closed_at = datetime.now(timezone.utc)

    closing_text = (
        "This chat has ended. Thanks for reaching out - "
        "feel free to send another message anytime."
    )

    existing_closing_message = (
        db.query(ConversationHistory)
        .filter(
            ConversationHistory.conversation_id
            == conversation_id,
            ConversationHistory.role == "system",
            ConversationHistory.message == closing_text,
        )
        .first()
    )

    if not existing_closing_message:
        db.add(
            ConversationHistory(
                conversation_id=conversation_id,
                role="system",
                message=closing_text,
            )
        )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    def _send_transcript_in_background(
        conv_id=conversation_id,
    ):
        from app.database import SessionLocal
        from app.services.summary_service import (
            generate_handoff_summary,
        )
        from app.services.pdf_service import (
            generate_handoff_pdf,
        )
        from app.services.email_service import (
            send_chat_completion_emails,
        )

        background_db = SessionLocal()

        try:
            summary = generate_handoff_summary(
                conv_id,
                background_db,
            )
            pdf_content = generate_handoff_pdf(
                conv_id,
                background_db,
            )

            if not pdf_content:
                print(
                    "⚠️ No messages found - skipping transcript "
                    f"PDF for {conv_id}"
                )
                return

            lead = (
                background_db.query(ContactInfo)
                .filter_by(conversation_id=conv_id)
                .first()
            )

            visitor_email = ""

            if (
                lead
                and lead.email
                and lead.email != "pending@example.com"
            ):
                visitor_email = lead.email

            send_chat_completion_emails(
                conv_id,
                pdf_content,
                summary or {},
                visitor_email,
            )
            print(
                "✅ Chat transcript emailed for conversation "
                f"{conv_id}"
            )
        except Exception as error:
            print(
                "⚠️ Failed to send end-of-chat transcript for "
                f"{conv_id}: {error}"
            )
        finally:
            background_db.close()

    threading.Thread(
        target=_send_transcript_in_background,
        daemon=True,
    ).start()

    return {
        "conversation_id": conversation_id,
        "mode": state.mode,
        "already_closed": False,
    }
