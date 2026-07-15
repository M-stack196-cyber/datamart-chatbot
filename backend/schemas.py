from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str
    role: Literal["employee", "customer"]
    department: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    department: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None


class ChatRequest(BaseModel):
    question: str


class DocumentResponse(BaseModel):
    id: int
    title: str
    filename: str
    content_type: Optional[str] = None
    visibility: Literal["internal", "external", "both"]
    status: str
    chunk_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentStatusUpdate(BaseModel):
    status: Literal["processing", "completed", "failed"]
    chunk_count: int


class UserAdminResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: Literal["admin", "employee", "customer"]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRoleUpdate(BaseModel):
    role: Literal["admin", "employee", "customer"]


class UserStatusUpdate(BaseModel):
    is_active: bool


class SimpleMessageResponse(BaseModel):
    message: str


class ConversationCreateResponse(BaseModel):
    id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackCreate(BaseModel):
    rating: Literal["up", "down"]
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: int
    message_id: int
    rating: Literal["up", "down"]
    comment: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatResponseEnvelope(BaseModel):
    payload: Any