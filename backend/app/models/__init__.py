from .user import User
from .contact_info import ContactInfo
from .conversation_history import ConversationHistory
from .conversation_state import ConversationState
from .project_requests import ProjectRequest
from .project_conversation import ProjectConversation
from .conversation_thread import Conversation
from .conversation import ChatConversation, ChatMessage, ChatSummary
from .documents import Document
from .message import Message
from .feedback import Feedback
from .meeting_booking import MeetingBooking

# Role constants - RESTORED hr and ceo
USER_ROLES = ["admin", "pmo", "cto", "hr", "ceo", "customer"]
STAFF_ROLES = ["admin", "pmo", "cto", "hr", "ceo"]
MANAGE_ROLES = ["admin", "pmo", "cto", "hr", "ceo"]
# New AI messages use "assistant". The "bot" role remains supported
# only for existing legacy chat records.
CANONICAL_MESSAGE_ROLES = ["user", "assistant", "agent", "system"]
LEGACY_MESSAGE_ROLES = ["bot"]
AI_MESSAGE_ROLES = ("assistant", "bot")
MESSAGE_ROLES = [*CANONICAL_MESSAGE_ROLES, *LEGACY_MESSAGE_ROLES]

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
CHAT_ROLES = MESSAGE_ROLES.copy()