from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.database import get_db
from app.services.lead_agent import LeadCaptureAgent
from app.core.security import get_current_user
from app.models.user import User
import uuid

router = APIRouter()

# Request models
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

# Active agents cache (use Redis in production)
active_agents = {}

# Placeholder for RAG service (you already have this)
async def process_rag_query(message: str, db: Session) -> str:
    """Placeholder for your existing RAG processing"""
    # This should call your existing RAG pipeline
    # For now, return a simple response
    return f"I understand you're asking about: {message}. Let me check the knowledge base."

@router.post("/chat-public")
async def public_chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """Public widget chat endpoint - Full lead capture"""
    conversation_id = request.conversation_id or str(uuid.uuid4())
    
    # Get or create agent for this conversation
    if conversation_id not in active_agents:
        active_agents[conversation_id] = LeadCaptureAgent(db, user=None)
    
    agent = active_agents[conversation_id]
    response, lead_complete = agent.process_message(conversation_id, request.message)
    
    # Fallback to RAG if no response from agent
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
    """Internal app chat endpoint - Logged-in users only"""
    conversation_id = request.conversation_id or f"internal_{current_user.id}"
    
    # Create agent with user context
    key = f"internal_{current_user.id}"
    if key not in active_agents:
        active_agents[key] = LeadCaptureAgent(db, user=current_user)
    
    agent = active_agents[key]
    response, request_complete = agent.process_message(conversation_id, request.message)
    
    # Fallback to RAG if no response from agent
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
    """Get conversation history for a lead (Admin only)"""
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