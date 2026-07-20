from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    phone = Column(String(30))
    role = Column(String(30), default="user")
    is_active = Column(Boolean, default=True)
    hashed_password = Column(String(255))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    project_requests = relationship("ProjectRequest", back_populates="user", cascade="all, delete-orphan")