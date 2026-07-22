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

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

active_agents = {}

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
    
    if conversation_id not in active_agents:
        active_agents[conversation_id] = LeadCaptureAgent(db, user=None)
    
    agent = active_agents[conversation_id]
    response, lead_complete = agent.process_message(conversation_id, request.message)
    
    if response is None:
        response = await process_rag_query(request.message, db)
    
    return {
        "response": response,
        "conversation_id": conversation_id,
        "lead_complete": lead_complete
    }

@router.post("/chat")
async def app_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation_id = request.conversation_id or f"internal_{current_user.id}"
    
    key = f"internal_{current_user.id}"
    if key not in active_agents:
        active_agents[key] = LeadCaptureAgent(db, user=current_user)
    
    agent = active_agents[key]
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
    
    if current_user.role not in ["admin", "cto", "pmo"]:
        raise HTTPException(403, "Insufficient permissions")
    
    lead = db.query(ContactInfo).filter(ContactInfo.conversation_id == conversation_id).first()
    if not lead:
        raise HTTPException(404, "Conversation not found")
    
    return {
        "lead": lead,
        "messages": lead.messages
    }