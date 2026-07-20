from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ProjectRequestBase(BaseModel):
    project_title: str = Field(..., min_length=3, max_length=255)
    project_description: str = Field(..., min_length=10)
    budget: Optional[str] = Field(None, max_length=100)
    timeline: Optional[str] = Field(None, max_length=100)
    priority: Optional[str] = "medium"
    department: Optional[str] = Field(None, max_length=100)
    is_urgent: Optional[bool] = False

class ProjectRequestCreate(ProjectRequestBase):
    user_id: int
    status: str = "pending"

class ProjectRequestUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[int] = None

class ProjectRequestResponse(ProjectRequestBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
