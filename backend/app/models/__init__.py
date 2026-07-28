from .user import User
from .contact_info import ContactInfo
from .conversation_history import ConversationHistory
from .conversation_state import ConversationState
from .project_requests import ProjectRequest
from .project_conversation import ProjectConversation
from .conversation import ChatConversation, ChatMessage, ChatSummary
from .documents import Document
from .message import Message
from .feedback import Feedback

# Aliases for backward compatibility
Conversation = ChatConversation

# Role constants
USER_ROLES = ["admin", "pmo", "cto", "customer"]
STAFF_ROLES = ["admin", "pmo", "cto"]
MANAGE_ROLES = ["admin", "pmo", "cto"]
MESSAGE_ROLES = ["user", "bot", "agent", "system"]

# Document constants
DOCUMENT_VISIBILITY = ["public", "private", "team"]
DOCUMENT_STATUS = ["draft", "published", "archived"]

# Contact constants
CONTACT_SOURCES = ["public_widget", "admin", "manual"]
CONTACT_STATUS = ["new", "contacted", "qualified", "converted", "lost"]

# Project constants
PROJECT_STATUS = ["pending", "in_progress", "review", "completed", "rejected", "on_hold"]
PROJECT_PRIORITY = ["low", "medium", "high", "urgent"]

# Chat constants
CHAT_MODES = ["bot", "pending_human", "human", "closed"]
CHAT_ROLES = ["user", "bot", "agent", "system"]
