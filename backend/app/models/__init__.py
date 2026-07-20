from .contact_info import ContactInfo
from .project_requests import ProjectRequest
from .conversation_history import ConversationHistory
from .project_conversation import ProjectConversation
from .user import User

# Document visibility and user roles
DOCUMENT_VISIBILITY = ["public", "internal", "private"]
USER_ROLES = ["admin", "user", "customer", "pmo", "cto"]
MESSAGE_ROLES = ["user", "assistant", "system"]

# Document model
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.database import Base

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100))
    visibility = Column(String(50), default="internal")
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    status = Column(String(50), default="processing")
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Conversation model
class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), default="New conversation")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Message model
class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Feedback model
class Feedback(Base):
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

__all__ = [
    "ContactInfo",
    "ProjectRequest",
    "ConversationHistory",
    "ProjectConversation",
    "User",
    "Document",
    "Conversation",
    "Message",
    "Feedback",
    "DOCUMENT_VISIBILITY",
    "USER_ROLES",
    "MESSAGE_ROLES"
]