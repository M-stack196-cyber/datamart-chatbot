from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


class ConversationState(Base):
    __tablename__ = "conversation_state"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String, nullable=False, index=True)  # Changed to String to support widget IDs
    
    lead_started = Column(Boolean, default=False)
    awaiting_field = Column(String, nullable=True)
    collected_data = Column(String, nullable=True)  # JSON string
    completed_fields = Column(String, nullable=True)  # JSON string
    optional_attempted = Column(String, nullable=True)  # JSON string
    skipped_fields = Column(String, nullable=True)  # JSON string
    
    mode = Column(String, default="bot")  # bot, pending_human, human
    assigned_agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    handoff_requested_at = Column(DateTime(timezone=True), nullable=True)
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    assigned_agent = relationship("User", foreign_keys=[assigned_agent_id])

    def __init__(self, **kwargs):
        # Extract conversation_id from kwargs manually
        conv_id = kwargs.pop("conversation_id", None)
        
        # Set it directly as a string (NO UUID CASTING)
        kwargs["conversation_id"] = conv_id
        
        # Let SQLAlchemy handle the rest of the initialization
        super().__init__(**kwargs)