from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class ChatConversation(Base):
    """Main conversation model for tracking chat sessions."""
    
    __tablename__ = "chat_conversations"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String(50), unique=True, index=True, nullable=False)
    visitor_name = Column(String(100), nullable=True)
    visitor_email = Column(String(100), nullable=True)
    visitor_phone = Column(String(20), nullable=True)
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user = relationship("User", back_populates="chat_conversations")
    
    chat_messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")
    chat_summary = relationship("ChatSummary", back_populates="conversation", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<ChatConversation(id={self.id}, conversation_id={self.conversation_id}, status={self.status})>"


class ChatMessage(Base):
    """Individual messages within a conversation."""
    
    __tablename__ = "chat_messages"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(Integer, nullable=True)
    role = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    conversation = relationship("ChatConversation", back_populates="chat_messages")
    
    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, conversation_id={self.conversation_id}, role={self.role})>"


class ChatSummary(Base):
    """Summary of a conversation for quick reference."""
    
    __tablename__ = "chat_summaries"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("chat_conversations.id", ondelete="CASCADE"), unique=True, nullable=False)
    summary = Column(Text, nullable=True)
    key_points = Column(Text, nullable=True)
    sentiment = Column(String(20), default="neutral")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    conversation = relationship("ChatConversation", back_populates="chat_summary")
    
    def __repr__(self) -> str:
        return f"<ChatSummary(id={self.id}, conversation_id={self.conversation_id}, sentiment={self.sentiment})>"