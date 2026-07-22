from sqlalchemy import Column, Integer, String, Text, DateTime, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid

class ContactInfo(Base):
    __tablename__ = "contact_info"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=False)
    project_description = Column(Text, nullable=False)
    
    company = Column(String(150), nullable=True)
    country = Column(String(100), nullable=True)
    project_title = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=True)
    budget = Column(String(100), nullable=True)
    timeline = Column(String(100), nullable=True)
    preferred_contact_method = Column(String(20), nullable=True)
    
    source = Column(String(30), nullable=False, default="public_widget")
    status = Column(String(30), nullable=False, default="new")
    lead_score = Column(Integer, default=0)
    assigned_to = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    messages = relationship("ConversationHistory", back_populates="lead", cascade="all, delete-orphan")
    
    def __init__(self, **kwargs):
        # Handle UUID conversion for SQLite
        if 'conversation_id' in kwargs:
            conv_id = kwargs['conversation_id']
            if isinstance(conv_id, str):
                kwargs['conversation_id'] = uuid.UUID(conv_id)
        super().__init__(**kwargs)