import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from app.database import get_db
from app.models import ChatConversation, ChatMessage

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

def get_ai_response(message: str) -> str:
    msg_lower = message.lower()
    if "services" in msg_lower:
        return "We offer Staff Augmentation, MVP Development, SaaS Maintenance, AI Automation, Custom Software, and Cloud & DevOps services."
    elif "cost" in msg_lower or "price" in msg_lower:
        return "Our pricing is 50-70% lower than US hiring with no recruiting fees. Contact us for a custom quote."
    elif "timeline" in msg_lower:
        return "We can start projects in 1-2 weeks for staff augmentation, and 8-12 weeks for MVP development."
    else:
        return "I'd be happy to help! We provide technology solutions including AI automation, custom software development, and cloud infrastructure. What specific service are you interested in?"

@router.post("/chat-public")
async def public_chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        conversation_id = request.conversation_id or str(uuid.uuid4())[:8]
        
        conv = db.query(ChatConversation).filter(
            ChatConversation.conversation_id == conversation_id
        ).first()
        
        if not conv:
            conv = ChatConversation(
                conversation_id=conversation_id,
                status="active"
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)
        
        response = get_ai_response(request.message)
        
        user_msg = ChatMessage(
            conversation_id=conv.id,
            role="user",
            message=request.message,
            timestamp=datetime.utcnow()
        )
        db.add(user_msg)
        
        bot_msg = ChatMessage(
            conversation_id=conv.id,
            role="bot",
            message=response,
            timestamp=datetime.utcnow()
        )
        db.add(bot_msg)
        db.commit()
        
        return {
            "response": response,
            "conversation_id": conversation_id,
            "mode": "bot",
            "lead_complete": False
        }
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return {"error": str(e)}

@router.get("/chat-public/{conversation_id}/history")
async def get_chat_history(conversation_id: str, db: Session = Depends(get_db)):
    conv = db.query(ChatConversation).filter(
        ChatConversation.conversation_id == conversation_id
    ).first()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conv.id
    ).order_by(ChatMessage.timestamp).all()
    
    return {
        "conversation_id": conversation_id,
        "status": conv.status,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "message": msg.message,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in messages
        ]
    }

@router.post("/chat-public/{conversation_id}/end")
async def end_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """End a conversation and trigger email notifications"""
    
    conv = db.query(ChatConversation).filter(
        ChatConversation.conversation_id == conversation_id
    ).first()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Mark as ended
    conv.status = "ended"
    conv.ended_at = datetime.utcnow()
    db.commit()
    
    # Import services
    try:
        from app.services.summary_service import generate_chat_summary
        from app.services.pdf_service import generate_chat_pdf
        from app.services.email_service import send_chat_completion_emails
    except ImportError as e:
        print(f"⚠️ Service import error: {e}")
        return {
            "status": "ended",
            "message": "Chat ended, but services not available.",
            "conversation_id": conversation_id
        }
    
    # Generate summary
    summary = generate_chat_summary(conv.id, db)
    
    # Generate PDF
    pdf_content = generate_chat_pdf(conversation_id, db)
    
    if not pdf_content:
        return {
            "status": "error",
            "message": "Failed to generate PDF",
            "conversation_id": conversation_id
        }
    
    # Send emails
    visitor_email = conv.visitor_email or ""
    send_chat_completion_emails(conversation_id, pdf_content, summary, visitor_email)
    
    return {
        "status": "ended",
        "message": "Chat ended and emails sent",
        "conversation_id": conversation_id,
        "summary": summary
    }
