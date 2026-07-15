from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

USER_ROLES = ("admin", "employee", "customer")
DOCUMENT_VISIBILITY = ("internal", "external", "both")
MESSAGE_ROLES = ("user", "assistant")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="customer")
    department = Column(String, nullable=True)  # e.g. "HR", "Finance", null for customers
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    documents = relationship("Document", back_populates="uploaded_by_user")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=True)
    visibility = Column(String(20), nullable=False, default="external")
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), nullable=False, default="processing")
    chunk_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    uploaded_by_user = relationship("User", back_populates="documents")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")
    feedback_items = relationship("Feedback", back_populates="message", cascade="all, delete-orphan")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    rating = Column(String(10), nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    message = relationship("Message", back_populates="feedback_items")