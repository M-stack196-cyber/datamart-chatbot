from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class LeadBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=5, max_length=30)
    project_description: str = Field(..., min_length=10)
    
    company: Optional[str] = Field(None, max_length=150)
    country: Optional[str] = Field(None, max_length=100)
    project_title: Optional[str] = Field(None, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    budget: Optional[str] = Field(None, max_length=100)
    timeline: Optional[str] = Field(None, max_length=100)
    preferred_contact_method: Optional[str] = Field(None, max_length=20)

class LeadCreate(LeadBase):
    conversation_id: Optional[UUID] = None
    source: str = "public_widget"
    status: str = "new"
    lead_score: Optional[int] = 0

class LeadUpdate(BaseModel):
    status: Optional[str] = None
    lead_score: Optional[int] = None
    assigned_to: Optional[int] = None

class LeadResponse(LeadBase):
    id: int
    conversation_id: UUID
    source: str
    status: str
    lead_score: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True