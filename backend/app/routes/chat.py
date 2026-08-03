import os
import requests
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timezone
from app.database import get_db
from app.services.lead_agent import LeadCaptureAgent
from app.dependencies import get_current_user
from app.models.user import User
from app.models.conversation_state import ConversationState
from app.models.conversation_history import ConversationHistory
from app.models.contact_info import ContactInfo
from app.models import Conversation, Message, STAFF_ROLES

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class AuthenticatedChatRequest(BaseModel):
    message: str
    conversation_id: int

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

    # Process with LeadCaptureAgent (restores lead capture & handoff)
    agent = LeadCaptureAgent(db, user=None)
    response, lead_complete = agent.process_message(conversation_id, request.message)

    # If no direct response and still in bot mode, use the existing
    # knowledge workflow. During lead-capture interruptions, answer the
    # visitor first and then resume the exact pending field.
    if response is None and agent.mode == "bot":
        response = await process_rag_query(request.message, db)

        if (
            agent.interruption_detected
            and agent.interruption_resume_prompt
        ):
            response = (
                f"{response}\n\n"
                "To continue your project request: "
                f"{agent.interruption_resume_prompt}"
            )

        # LeadCaptureAgent already stored the visitor's message. Store the
        # RAG-generated assistant response exactly once as well.
        agent._save_message(
            conversation_id,
            "assistant",
            response,
        )

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
    if state.mode == "human" and state.assigned_agent:
        agent_name = state.assigned_agent.display_name

    return {"mode": state.mode, "agent_name": agent_name}


@router.get("/chat-public/{conversation_id}/messages")
async def public_chat_messages(
    conversation_id: str,
    after_id: int = 0,
    db: Session = Depends(get_db)
):
    """Polling endpoint for the widget while mode is pending_human/human -
    returns any new messages (including the staff member's replies) since
    `after_id`."""
    
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
            {
                "id": m.id,
                "role": m.role,
                "message": m.message,
                "created_at": m.created_at
            }
            for m in messages
        ]
    }

@router.post("/chat")
async def app_chat(
    request: AuthenticatedChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    # Keep each authenticated sidebar conversation's agent state isolated.
    agent_state_id = (
        f"internal_{current_user.id}_{conversation.id}"
    )

    agent = LeadCaptureAgent(db, user=current_user)
    response, request_complete = agent.process_message(
        agent_state_id,
        request.message,
    )

    if response is None:
        response = await process_rag_query(
            request.message,
            db,
        )

    existing_message_count = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .count()
    )

    if (
        existing_message_count == 0
        and (
            not conversation.title
            or conversation.title == "New conversation"
        )
    ):
        compact_title = " ".join(
            request.message.strip().split()
        )
        conversation.title = (
            compact_title[:40]
            if compact_title
            else "New conversation"
        )

    db.add(
        Message(
            conversation_id=conversation.id,
            role="user",
            content=request.message,
        )
    )

    if response:
        db.add(
            Message(
                conversation_id=conversation.id,
                role="assistant",
                content=response,
            )
        )

    conversation.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "response": response,
        "conversation_id": conversation.id,
        "request_complete": request_complete,
        "user": {
            "name": current_user.full_name,
            "email": current_user.email,
            "role": getattr(
                current_user,
                "role",
                "user",
            ),
        },
    }


@router.get("/chat/conversation/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in STAFF_ROLES:
        raise HTTPException(403, "Insufficient permissions")

    lead = db.query(ContactInfo).filter(ContactInfo.conversation_id == conversation_id).first()
    if not lead:
        raise HTTPException(404, "Conversation not found")

    return {
        "lead": lead,
        "messages": lead.messages
    }


# === Endpoint to get history for a returning visitor ===
@router.get("/chat-public/{conversation_id}/history")
async def get_chat_history_from_new_tables(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Get full chat history so a returning visitor sees their past messages."""
    
    messages = (
        db.query(ConversationHistory)
        .filter(ConversationHistory.conversation_id == conversation_id)
        .order_by(ConversationHistory.id.asc())
        .all()
    )
    
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        "conversation_id": conversation_id,
        "status": "active",
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "message": m.message,
                "timestamp": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ]
    }

# === Endpoint to get summary ===
@router.get("/chat-public/{conversation_id}/summary")
async def get_chat_summary(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Get chat summary for a visitor conversation."""

    from app.services.summary_service import generate_handoff_summary

    summary = generate_handoff_summary(conversation_id, db)

    if not summary:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return summary


# === Endpoint to end conversation and trigger email ===
@router.post("/chat-public/{conversation_id}/end")
async def end_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """End a conversation and trigger email notifications."""

    from app.services.summary_service import generate_handoff_summary
    from app.services.pdf_service import generate_handoff_pdf
    from app.services.email_service import send_chat_completion_emails

    summary = generate_handoff_summary(conversation_id, db)
    pdf_content = generate_handoff_pdf(conversation_id, db)

    if not pdf_content:
        raise HTTPException(status_code=404, detail="Conversation not found")

    lead = db.query(ContactInfo).filter_by(conversation_id=conversation_id).first()
    visitor_email = ""
    if lead and lead.email and lead.email != "pending@example.com":
        visitor_email = lead.email

    send_chat_completion_emails(conversation_id, pdf_content, summary or {}, visitor_email)

    return {
        "status": "ended",
        "message": "Chat ended and emails sent",
        "conversation_id": conversation_id,
        "summary": summary
    }