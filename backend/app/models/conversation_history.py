from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid

class ConversationHistory(Base):
    __tablename__ = "conversation_history"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("contact_info.conversation_id"), nullable=False)
    role = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    lead = relationship("ContactInfo", back_populates="messages")
    
    def __init__(self, **kwargs):
        # Handle UUID conversion for SQLite
        if 'conversation_id' in kwargs:
            conv_id = kwargs['conversation_id']
            if isinstance(conv_id, str):
                kwargs['conversation_id'] = uuid.UUID(conv_id)
        super().__init__(**kwargs)
