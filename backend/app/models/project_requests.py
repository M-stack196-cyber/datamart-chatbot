from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class ProjectRequest(Base):
    """Project request model for user project submissions."""
    
    __tablename__ = "project_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
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
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships - FIXED: Added foreign_keys to user relationship
    user = relationship("User", foreign_keys=[user_id], back_populates="project_requests")
    assignee = relationship("User", foreign_keys=[assigned_to], backref="assigned_projects")
    messages = relationship("ProjectConversation", back_populates="request", cascade="all, delete-orphan")
    
    # Indexes for better performance
    __table_args__ = (
        Index("ix_project_requests_user_id", "user_id"),
        Index("ix_project_requests_status", "status"),
        Index("ix_project_requests_assigned_to", "assigned_to"),
        Index("ix_project_requests_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<ProjectRequest(id={self.id}, title={self.title}, status={self.status})>"
    
    def __str__(self) -> str:
        return f"{self.project_title} ({self.status})"
    
    @property
    def is_pending(self) -> bool:
        """Check if request is pending."""
        return self.status == "pending"
    
    @property
    def is_in_progress(self) -> bool:
        """Check if request is in progress."""
        return self.status == "in_progress"
    
    @property
    def is_completed(self) -> bool:
        """Check if request is completed."""
        return self.status == "completed"
    
    @property
    def is_rejected(self) -> bool:
        """Check if request is rejected."""
        return self.status == "rejected"
    
    def update_status(self, new_status: str) -> None:
        """Update the status of the project request."""
        valid_statuses = ["pending", "in_progress", "review", "completed", "rejected", "on_hold"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        self.status = new_status