from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from . import Document, ProjectRequest
    from .contact_info import ContactInfo
    from .conversation_history import ConversationHistory
    from .project_conversation import ProjectConversation
    from .conversation import ChatConversation


class User(Base):
    """User model representing system users with role-based access."""
    
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # User information
    email: Mapped[str] = mapped_column(String(255), unique=False, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    role: Mapped[str] = mapped_column(String(30), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Live handoff: whether this staff member is currently available to take live chats
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    last_active_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships - using string references to avoid circular imports
    project_requests: Mapped[List["ProjectRequest"]] = relationship(
        "ProjectRequest", 
        foreign_keys="ProjectRequest.user_id",
        back_populates="user", 
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    documents: Mapped[List["Document"]] = relationship(
        "Document", 
        back_populates="uploader",
        foreign_keys="Document.uploaded_by",
        cascade="all, delete-orphan"
    )
    
    conversations: Mapped[List["ChatConversation"]] = relationship(
        "ChatConversation", 
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    contact_infos: Mapped[List["ContactInfo"]] = relationship(
        "ContactInfo",
        foreign_keys="ContactInfo.assigned_to",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    conversation_histories: Mapped[List["ConversationHistory"]] = relationship(
        "ConversationHistory",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    project_conversations: Mapped[List["ProjectConversation"]] = relationship(
        "ProjectConversation",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # Indexes for better performance
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_role", "role"),
        Index("ix_users_is_active", "is_active"),
        Index("ix_users_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    def __str__(self) -> str:
        return f"{self.full_name} ({self.email})"
    
    @property
    def is_admin(self) -> bool:
        return self.role == "admin"
    
    @property
    def is_customer(self) -> bool:
        return self.role == "customer"
    
    @property
    def is_pmo(self) -> bool:
        return self.role == "pmo"
    
    @property
    def is_cto(self) -> bool:
        return self.role == "cto"
    
    @property
    def display_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        else:
            return self.full_name or self.email
    
    @property
    def full_name_display(self) -> str:
        return self.display_name
    
    def has_role(self, role: str) -> bool:
        return self.role == role
    
    def has_any_role(self, roles: List[str]) -> bool:
        return self.role in roles
    
    @classmethod
    def get_valid_roles(cls) -> List[str]:
        from . import USER_ROLES
        return USER_ROLES
