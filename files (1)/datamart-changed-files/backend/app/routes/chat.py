import os
import requests
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.database import get_db
from app.services.lead_agent import LeadCaptureAgent
from app.core.security import get_current_user
from app.models.user import User
from app.models.conversation_state import ConversationState
from app.models.conversation_history import ConversationHistory
from app.models import STAFF_ROLES

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

async def process_rag_query(message: str, db: Session) -> str:
    """Call the n8n chat-query workflow for general questions"""
    webhook_url = os.getenv("N8N_CHAT_WEBHOOK_URL")

    if not webhook_url:
        return "I'm having trouble connecting to my knowledge base right now. Please try again in a moment."

    try:
        response = requests.post(
            webhook_url,
            json={"question": message},
            timeout=45
        )
        response.raise_for_status()
        data = response.json()
        return data.get("answer", "I couldn't find an answer to your question.")
    except Exception as e:
        print(f"RAG error: {e}")
        return "I'm having trouble connecting to my knowledge base right now. Please try again in a moment."


@router.post("/chat-public")
async def public_chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    conversation_id = request.conversation_id or str(uuid.uuid4())

    # NOTE: state is no longer kept in an in-memory dict. The backend runs on
    # serverless functions, so a fresh LeadCaptureAgent is created on every
    # request and reloads its progress from the conversation_state table
    # (see LeadCaptureAgent._load_state). This is what fixes the bug where
    # the bot used to "forget" the conversation after the first reply.
    agent = LeadCaptureAgent(db, user=None)
    response, lead_complete = agent.process_message(conversation_id, request.message)

    # agent.mode reflects the conversation state AFTER this message was
    # processed - it may have just flipped to "pending_human" if the user
    # asked to talk to someone.
    if response is None and agent.mode == "bot":
        response = await process_rag_query(request.message, db)

    return {
        "response": response,
        "conversation_id": conversation_id,
        "lead_complete": lead_complete,
        "mode": agent.mode,  # "bot" | "pending_human" | "human" | "closed"
    }


@router.get("/chat-public/{conversation_id}/status")
async def public_chat_status(conversation_id: str, db: Session = Depends(get_db)):
    """Lets the widget poll whether it's still waiting for a human, or has
    been connected, without sending a new chat message."""
    state = db.query(ConversationState).filter_by(conversation_id=conversation_id).first()
    if not state:
        return {"mode": "bot", "agent_name": None}

    agent_name = None
    if state.mode == "human" and state.agent:
        agent_name = state.agent.display_name

    return {"mode": state.mode, "agent_name": agent_name}


@router.get("/chat-public/{conversation_id}/messages")
async def public_chat_messages(
    conversation_id: str,
    after_id: int = 0,
    db: Session = Depends(get_db)
):
    """Polling endpoint for the widget while mode is pending_human/human -
    returns any new messages (including the staff member's replies) since
    `after_id`. The frontend should poll this every few seconds once the
    /chat-public response comes back with mode != "bot"."""
    messages = (
        db.query(ConversationHistory)
        .filter(
            ConversationHistory.conversation_id == conversation_id,
            ConversationHistory.id > after_id,
        )
        .order_by(ConversationHistory.id.asc())
        .all()
    )
    return {
        "messages": [
            {"id": m.id, "role": m.role, "message": m.message, "created_at": m.created_at}
            for m in messages
        ]
    }


@router.post("/chat")
async def app_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation_id = request.conversation_id or f"internal_{current_user.id}"

    agent = LeadCaptureAgent(db, user=current_user)
    response, request_complete = agent.process_message(conversation_id, request.message)

    if response is None:
        response = await process_rag_query(request.message, db)

    return {
        "response": response,
        "conversation_id": conversation_id,
        "request_complete": request_complete,
        "user": {
            "name": current_user.full_name,
            "email": current_user.email,
            "role": getattr(current_user, 'role', 'user')
        }
    }

@router.get("/chat/conversation/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.models.contact_info import ContactInfo

    if current_user.role not in STAFF_ROLES:
        raise HTTPException(403, "Insufficient permissions")

    lead = db.query(ContactInfo).filter(ContactInfo.conversation_id == conversation_id).first()
    if not lead:
        raise HTTPException(404, "Conversation not found")

    return {
        "lead": lead,
        "messages": lead.messages
    }
