from sqlalchemy import Column, Integer, String, Text, DateTime, UUID, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid


class ContactInfo(Base):
    """Contact information model for lead management."""
    
    __tablename__ = "contact_info"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # Required fields
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=False)
    project_description = Column(Text, nullable=False)
    
    # Optional fields
    company = Column(String(150), nullable=True)
    country = Column(String(100), nullable=True)
    project_title = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=True)
    budget = Column(String(100), nullable=True)
    timeline = Column(String(100), nullable=True)
    preferred_contact_method = Column(String(20), nullable=True)
    
    # System fields
    source = Column(String(30), nullable=False, default="public_widget")
    status = Column(String(30), nullable=False, default="new")
    lead_score = Column(Integer, default=0)
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships - FIXED: Added overlaps to resolve warnings
    messages = relationship("ConversationHistory", back_populates="lead", cascade="all, delete-orphan")
    
    # User relationships with overlaps to resolve foreign key conflicts
    user = relationship("User", foreign_keys=[assigned_to], back_populates="contact_infos", overlaps="assignee")
    assignee = relationship("User", foreign_keys=[assigned_to], overlaps="user")
    updater = relationship("User", foreign_keys=[updated_by])
    
    # Indexes for better performance
    __table_args__ = (
        Index("ix_contact_info_conversation_id", "conversation_id"),
        Index("ix_contact_info_assigned_to", "assigned_to"),
        Index("ix_contact_info_updated_by", "updated_by"),
        Index("ix_contact_info_status", "status"),
        Index("ix_contact_info_created_at", "created_at"),
    )
    
    def __init__(self, **kwargs):
        """Handle UUID conversion for SQLite compatibility."""
        if 'conversation_id' in kwargs:
            conv_id = kwargs['conversation_id']
            if isinstance(conv_id, str):
                kwargs['conversation_id'] = uuid.UUID(conv_id)
        super().__init__(**kwargs)
    
    def __repr__(self) -> str:
        return f"<ContactInfo(id={self.id}, name={self.name}, email={self.email})>"
    
    def __str__(self) -> str:
        return f"{self.name} ({self.email})"
    
    @property
    def is_new(self) -> bool:
        """Check if contact is new."""
        return self.status == "new"
    
    @property
    def is_contacted(self) -> bool:
        """Check if contact has been contacted."""
        return self.status == "contacted"
    
    @property
    def is_qualified(self) -> bool:
        """Check if contact is qualified."""
        return self.status == "qualified"
    
    @property
    def is_converted(self) -> bool:
        """Check if contact has been converted."""
        return self.status == "converted"
    
    @property
    def is_lost(self) -> bool:
        """Check if contact is lost."""
        return self.status == "lost"
    
    def update_status(self, new_status: str) -> None:
        """Update the status of the contact."""
        valid_statuses = ["new", "contacted", "qualified", "converted", "lost"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        self.status = new_status