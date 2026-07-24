from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UUID, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid


class ConversationHistory(Base):
    """Conversation history model for lead interactions."""
    
    __tablename__ = "conversation_history"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("contact_info.conversation_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    lead = relationship("ContactInfo", back_populates="messages")
    
    # User relationship (matching back_populates in user.py)
    user = relationship("User", back_populates="conversation_histories")
    
    # Indexes for better performance
    __table_args__ = (
        Index("ix_conversation_history_conversation_id", "conversation_id"),
        Index("ix_conversation_history_user_id", "user_id"),
        Index("ix_conversation_history_role", "role"),
        Index("ix_conversation_history_created_at", "created_at"),
    )
    
    def __init__(self, **kwargs):
        """Handle UUID conversion for SQLite compatibility."""
        if 'conversation_id' in kwargs:
            conv_id = kwargs['conversation_id']
            if isinstance(conv_id, str):
                kwargs['conversation_id'] = uuid.UUID(conv_id)
        super().__init__(**kwargs)
    
    def __repr__(self) -> str:
        return f"<ConversationHistory(id={self.id}, conversation_id={self.conversation_id}, role={self.role})>"
    
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