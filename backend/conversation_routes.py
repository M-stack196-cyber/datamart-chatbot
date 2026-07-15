from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models import Conversation, Feedback, Message, MESSAGE_ROLES, User
from schemas import (
    ConversationCreateResponse,
    ConversationResponse,
    FeedbackCreate,
    FeedbackResponse,
    MessageCreate,
    MessageResponse,
    SimpleMessageResponse,
)

router = APIRouter(tags=["conversations"])


def _conversation_for_user_or_404(db: Session, conversation_id: int, user_id: int) -> Conversation:
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if conversation.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return conversation


def _auto_title(text: str) -> str:
    compact = " ".join(text.strip().split())
    return compact[:40] if compact else "New conversation"


@router.post("/conversations", response_model=ConversationCreateResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = Conversation(user_id=current_user.id, title="New conversation")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _conversation_for_user_or_404(db, conversation_id, current_user.id)
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def create_message(
    conversation_id: int,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.role not in MESSAGE_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid message role")

    conversation = _conversation_for_user_or_404(db, conversation_id, current_user.id)

    message = Message(conversation_id=conversation_id, role=payload.role, content=payload.content)
    db.add(message)
    db.flush()

    existing_count = db.query(Message).filter(Message.conversation_id == conversation_id).count()
    if existing_count == 1 and (not conversation.title or conversation.title == "New conversation"):
        conversation.title = _auto_title(payload.content)

    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(message)
    return message


@router.delete("/conversations/{conversation_id}", response_model=SimpleMessageResponse)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = _conversation_for_user_or_404(db, conversation_id, current_user.id)
    db.delete(conversation)
    db.commit()
    return {"message": "Conversation deleted"}


@router.post("/messages/{message_id}/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def create_feedback(
    message_id: int,
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    conversation = _conversation_for_user_or_404(db, message.conversation_id, current_user.id)
    _ = conversation

    feedback = Feedback(message_id=message_id, rating=payload.rating, comment=payload.comment)
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback
