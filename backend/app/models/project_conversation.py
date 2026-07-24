from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class ProjectConversation(Base):
    """Project conversation model for project-specific interactions."""
    
    __tablename__ = "project_conversation"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("project_requests.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    request = relationship("ProjectRequest", back_populates="messages")
    user = relationship("User", back_populates="project_conversations")
    
    # Indexes for better performance
    __table_args__ = (
        Index("ix_project_conversation_request_id", "request_id"),
        Index("ix_project_conversation_user_id", "user_id"),
        Index("ix_project_conversation_role", "role"),
        Index("ix_project_conversation_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<ProjectConversation(id={self.id}, request_id={self.request_id}, role={self.role})>"
    
    def __str__(self) -> str:
        return f"{self.role}: {self.message[:50]}..."
    
    @property
    def is_user_message(self) -> bool:
        """Check if message is from user."""
        return self.role == "user"
    
    @property
    def is_assistant_message(self) -> bool:
        """Check if message is from assistant."""
        return self.role == "assistant"
    
    @property
    def is_system_message(self) -> bool:
        """Check if message is from system."""
        return self.role == "system"
    
    @property
    def message_preview(self) -> str:
        """Get a preview of the message (first 100 characters)."""
        return self.message[:100] + "..." if len(self.message) > 100 else self.message