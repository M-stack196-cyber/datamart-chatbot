from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str = "user"

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Admin schemas
class DocumentResponse(BaseModel):
    id: int
    title: str
    filename: str
    content_type: Optional[str] = None
    visibility: str
    uploaded_by: int
    status: str
    chunk_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DocumentStatusUpdate(BaseModel):
    status: str
    chunk_count: Optional[int] = None

class SimpleMessageResponse(BaseModel):
    message: str

class UserAdminResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserRoleUpdate(BaseModel):
    role: str

class UserStatusUpdate(BaseModel):
    is_active: bool

# Chat schemas
class ChatRequest(BaseModel):
    question: str

# Conversation schemas
class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ConversationCreateResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    role: str
    content: str

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class FeedbackCreate(BaseModel):
    rating: int
    comment: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: int
    message_id: int
    rating: int
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# Lead schemas
from .lead import LeadBase, LeadCreate, LeadUpdate, LeadResponse
from .project_request import ProjectRequestBase, ProjectRequestCreate, ProjectRequestUpdate, ProjectRequestResponse

__all__ = [
    "Token",
    "UserCreate",
    "UserResponse",
    "DocumentResponse",
    "DocumentStatusUpdate",
    "SimpleMessageResponse",
    "UserAdminResponse",
    "UserRoleUpdate",
    "UserStatusUpdate",
    "ChatRequest",
    "ConversationResponse",
    "ConversationCreateResponse",
    "MessageCreate",
    "MessageResponse",
    "FeedbackCreate",
    "FeedbackResponse",
    "LeadBase",
    "LeadCreate",
    "LeadUpdate",
    "LeadResponse",
    "ProjectRequestBase",
    "ProjectRequestCreate",
    "ProjectRequestUpdate",
    "ProjectRequestResponse"
]