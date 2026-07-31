from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ConversationState(Base):
    __tablename__ = "conversation_state"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )
    
    lead_started = Column(Boolean, default=False)
    awaiting_field = Column(String, nullable=True)
    collected_data = Column(String, nullable=True)  # JSON string
    completed_fields = Column(String, nullable=True)  # JSON string
    optional_attempted = Column(String, nullable=True)  # JSON string
    skipped_fields = Column(String, nullable=True)  # JSON string
    
    mode = Column(String, default="bot")  # bot, pending_human, human, closed
    assigned_agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    handoff_requested_at = Column(DateTime(timezone=True), nullable=True)
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    assigned_agent = relationship("User", foreign_keys=[assigned_agent_id])
