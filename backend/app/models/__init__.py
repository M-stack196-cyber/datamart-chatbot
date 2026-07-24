# Standard library imports
from typing import List, Optional

# SQLAlchemy imports
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# Application imports
from app.database import Base

# Import existing models
from .contact_info import ContactInfo
from .project_requests import ProjectRequest
from .conversation_history import ConversationHistory
from .project_conversation import ProjectConversation
from .user import User

# Document visibility and user roles
DOCUMENT_VISIBILITY: List[str] = ["public", "internal", "private", "external"]
USER_ROLES: List[str] = ["admin", "user", "customer", "pmo", "cto"]
MESSAGE_ROLES: List[str] = ["user", "assistant", "system"]


class Document(Base):
    """Document model for file uploads and management."""
    
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=True)
    visibility = Column(String(50), default="internal")
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default="processing")
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    uploader = relationship("User", back_populates="documents", foreign_keys=[uploaded_by])
    
    # Indexes for better performance
    __table_args__ = (
        Index("ix_documents_uploaded_by", "uploaded_by"),
        Index("ix_documents_visibility", "visibility"),
        Index("ix_documents_status", "status"),
        Index("ix_documents_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title={self.title}, filename={self.filename})>"


class Conversation(Base):
    """Conversation model for chat sessions."""
    
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), default="New conversation")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", lazy="dynamic")
    
    # Indexes for better performance
    __table_args__ = (
        Index("ix_conversations_user_id", "user_id"),
        Index("ix_conversations_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, user_id={self.user_id}, title={self.title})>"


class Message(Base):
    """Message model for conversation entries."""
    
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    feedback = relationship("Feedback", back_populates="message", cascade="all, delete-orphan", uselist=False)
    
    # Indexes for better performance
    __table_args__ = (
        Index("ix_messages_conversation_id", "conversation_id"),
        Index("ix_messages_role", "role"),
        Index("ix_messages_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, role={self.role})>"


class Feedback(Base):
    """Feedback model for message ratings."""
    
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, unique=True)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    message = relationship("Message", back_populates="feedback")
    
    # Indexes for better performance
    __table_args__ = (
        Index("ix_feedback_message_id", "message_id"),
        Index("ix_feedback_rating", "rating"),
        Index("ix_feedback_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Feedback(id={self.id}, message_id={self.message_id}, rating={self.rating})>"
    
    @property
    def is_positive(self) -> bool:
        """Check if feedback is positive (rating >= 4)."""
        return self.rating >= 4
    
    @property
    def is_negative(self) -> bool:
        """Check if feedback is negative (rating <= 2)."""
        return self.rating <= 2


# Update __all__ to include all public objects
__all__ = [
    # Imported models
    "ContactInfo",
    "ProjectRequest",
    "ConversationHistory",
    "ProjectConversation",
    "User",
    
    # Local models
    "Document",
    "Conversation",
    "Message",
    "Feedback",
    
    # Constants
    "DOCUMENT_VISIBILITY",
    "USER_ROLES",
    "MESSAGE_ROLES"
]