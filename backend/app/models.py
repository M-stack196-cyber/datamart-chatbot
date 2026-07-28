# app/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

# ============================================================
# CHAT HISTORY MODELS
# ============================================================

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String(50), unique=True, index=True, nullable=False)
    visitor_name = Column(String(100), nullable=True)
    visitor_email = Column(String(100), nullable=True)
    visitor_phone = Column(String(20), nullable=True)
    status = Column(String(20), default="active")  # active, ended, transferred
    created_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")
    summary = relationship("ChatSummary", back_populates="conversation", uselist=False, cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    message_id = Column(Integer, nullable=True)
    role = Column(String(20))  # user, bot, agent
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="messages")

class ChatSummary(Base):
    __tablename__ = "chat_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), unique=True)
    summary = Column(Text)
    key_points = Column(Text)
    sentiment = Column(String(20), default="neutral")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="summary")
