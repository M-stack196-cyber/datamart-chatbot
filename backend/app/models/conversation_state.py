from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UUID, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid


class ConversationState(Base):
    """
    Persists chatbot conversation state to the database instead of server memory.

    Why this exists: the backend is deployed on Vercel serverless functions, which
    do not guarantee the same process/memory handles two consecutive requests.
    Any state kept only in a Python variable (e.g. a module-level dict) can vanish
    between one user message and the next. This table makes lead-capture progress
    AND bot/human handoff status durable across requests.
    """

    __tablename__ = "conversation_state"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(UUID(as_uuid=True), unique=True, index=True, nullable=False)

    # --- Lead-capture agent progress ---
    lead_started = Column(Boolean, default=False)
    awaiting_field = Column(String(50), nullable=True)
    collected_data = Column(Text, default="{}")       # JSON-encoded dict
    completed_fields = Column(Text, default="[]")     # JSON-encoded list
    optional_attempted = Column(Text, default="[]")   # JSON-encoded list
    skipped_fields = Column(Text, default="[]")       # JSON-encoded list

    # --- Bot / human handoff status ---
    # bot            -> normal chatbot handles the conversation
    # pending_human  -> user asked to talk to someone; waiting for a staff member to claim it
    # human          -> a staff member has claimed it; bot stays silent, messages relay directly
    # closed         -> handoff ended, back to normal (or conversation finished)
    mode = Column(String(20), default="bot", nullable=False)
    assigned_agent_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    handoff_requested_at = Column(DateTime(timezone=True), nullable=True)
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    agent = relationship("User", foreign_keys=[assigned_agent_id])

    __table_args__ = (
        Index("ix_conversation_state_conversation_id", "conversation_id"),
        Index("ix_conversation_state_mode", "mode"),
    )

    def __init__(self, **kwargs):
        if "conversation_id" in kwargs:
            conv_id = kwargs["conversation_id"]
            if isinstance(conv_id, str):
                kwargs["conversation_id"] = uuid.UUID(conv_id)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<ConversationState(conversation_id={self.conversation_id}, mode={self.mode})>"
