from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class ProjectRequest(Base):
    __tablename__ = "project_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Project details
    project_title = Column(String(255), nullable=False)
    project_description = Column(Text, nullable=False)
    
    # Optional details
    budget = Column(String(100), nullable=True)
    timeline = Column(String(100), nullable=True)
    priority = Column(String(20), default="medium")
    department = Column(String(100), nullable=True)
    
    # Metadata
    status = Column(String(30), nullable=False, default="pending")
    is_urgent = Column(Boolean, default=False)
    assigned_to = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="project_requests")
    messages = relationship("ProjectConversation", back_populates="request", cascade="all, delete-orphan")