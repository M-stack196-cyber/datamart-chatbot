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
    """A staff member claims a pending live-chat request. Whoever claims it
    first wins - the bot stops responding and the claiming employee talks
    directly to the visitor from here on."""
    state = db.query(ConversationState).filter_by(conversation_id=conversation_id).first()
    if not state:
        raise HTTPException(404, "Conversation not found")

    if state.mode == "human" and state.assigned_agent_id != current_user.id:
        raise HTTPException(409, "This chat has already been claimed by another team member")

    state.mode = "human"
    state.assigned_agent_id = current_user.id
    state.claimed_at = datetime.now(timezone.utc)
    db.commit()

    # Let the visitor know a human has joined (only if not already sent)
    # Use "system" role instead of "agent" so widget treats it differently
    existing_join = db.query(ConversationHistory).filter(
        ConversationHistory.conversation_id == conversation_id,
        ConversationHistory.role.in_(["agent", "system"]),
        ConversationHistory.message.contains("joined the chat")
    ).first()

    if not existing_join:
        joined_msg = ConversationHistory(
            conversation_id=conversation_id,
            role="system",
            message=f"{current_user.display_name} from Datamart has joined the chat. How can I help?",
        )
        db.add(joined_msg)
        db.commit()
        print(f"✅ Join message sent for conversation {conversation_id}")
    else:
        print(f"⚠️ Join message already exists for conversation {conversation_id}")

    return {"conversation_id": conversation_id, "mode": state.mode, "assigned_to": current_user.display_name}


@router.get("/handoff/{conversation_id}/messages")
def get_handoff_messages(
    conversation_id: str,
    current_user: User = Depends(require_role(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    """Full transcript for the staff member's chat panel."""
    state = db.query(ConversationState).filter_by(conversation_id=conversation_id).first()
    if not state:
        raise HTTPException(404, "Conversation not found")

    messages = (
        db.query(ConversationHistory)
        .filter(ConversationHistory.conversation_id == conversation_id)
        .order_by(ConversationHistory.id.asc())
        .all()
    )
    return {
        "mode": state.mode,
        "assigned_agent_id": state.assigned_agent_id,
        "messages": [
            {"id": m.id, "role": m.role, "message": m.message, "created_at": m.created_at}
            for m in messages
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
    """Staff member sends a reply directly to the visitor. This is what the
    visitor's widget picks up via GET /chat-public/{id}/messages polling."""
    state = db.query(ConversationState).filter_by(conversation_id=conversation_id).first()
    if not state:
        raise HTTPException(404, "Conversation not found")
    if state.mode != "human" or state.assigned_agent_id != current_user.id:
        raise HTTPException(403, "You have not claimed this conversation")

    # 🔥 FIX: Check for duplicate messages before saving (with time window)
    # Check if the exact same message was sent by the same agent in the last 5 seconds
    time_threshold = datetime.now(timezone.utc) - timedelta(seconds=5)
    recent_msg = db.query(ConversationHistory).filter(
        ConversationHistory.conversation_id == conversation_id,
        ConversationHistory.role == "agent",
        ConversationHistory.message == payload.message,
        ConversationHistory.created_at >= time_threshold
    ).first()

    if recent_msg:
        print(f"⚠️ Duplicate message detected (within 5s), not saving: {payload.message[:50]}")
        return {"id": recent_msg.id, "role": recent_msg.role, "message": recent_msg.message, "created_at": recent_msg.created_at}

    msg = ConversationHistory(
        conversation_id=conversation_id,
        role="agent",
        message=payload.message,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return {"id": msg.id, "role": msg.role, "message": msg.message, "created_at": msg.created_at}


@router.post("/handoff/{conversation_id}/end")
def end_handoff(
    conversation_id: str,
    current_user: User = Depends(require_role(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    """End the live chat. Conversation goes back to bot mode in case the
    visitor keeps chatting, but the bot won't re-trigger lead capture from
    scratch since lead_started/collected_data are preserved."""
    state = db.query(ConversationState).filter_by(conversation_id=conversation_id).first()
    if not state:
        raise HTTPException(404, "Conversation not found")
    if state.assigned_agent_id != current_user.id:
        raise HTTPException(403, "You are not assigned to this conversation")

    state.mode = "closed"
    state.closed_at = datetime.now(timezone.utc)
    db.commit()

    closing_msg = ConversationHistory(
        conversation_id=conversation_id,
        role="system",
        message="This chat has ended. Thanks for reaching out - feel free to send another message anytime.",
    )
    db.add(closing_msg)
    db.commit()

    return {"conversation_id": conversation_id, "mode": state.mode}