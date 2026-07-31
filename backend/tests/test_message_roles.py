from types import SimpleNamespace

from app.models import (
    AI_MESSAGE_ROLES,
    CANONICAL_MESSAGE_ROLES,
    CHAT_ROLES,
    LEGACY_MESSAGE_ROLES,
    MESSAGE_ROLES,
)
from app.services.pdf_service import TRANSCRIPT_ROLE_LABELS
from app.services.summary_service import generate_handoff_summary


class FakeQuery:
    def __init__(self, messages):
        self.messages = messages

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return self.messages


class FakeSession:
    def __init__(self, messages):
        self.messages = messages

    def query(self, _model):
        return FakeQuery(self.messages)


def test_message_role_constants_preserve_legacy_bot_compatibility():
    assert CANONICAL_MESSAGE_ROLES == [
        "user",
        "assistant",
        "agent",
        "system",
    ]
    assert LEGACY_MESSAGE_ROLES == ["bot"]
    assert AI_MESSAGE_ROLES == ("assistant", "bot")

    assert MESSAGE_ROLES == [
        "user",
        "assistant",
        "agent",
        "system",
        "bot",
    ]
    assert CHAT_ROLES == MESSAGE_ROLES


def test_transcript_labels_treat_assistant_and_bot_as_ai():
    assert TRANSCRIPT_ROLE_LABELS["user"] == "VISITOR"
    assert TRANSCRIPT_ROLE_LABELS["assistant"] == "BOT"
    assert TRANSCRIPT_ROLE_LABELS["bot"] == "BOT"
    assert TRANSCRIPT_ROLE_LABELS["agent"] == "AGENT"
    assert TRANSCRIPT_ROLE_LABELS["system"] == "SYSTEM"


def test_handoff_summary_counts_current_and_legacy_ai_roles():
    messages = [
        SimpleNamespace(
            role="user",
            message="This is a great service project.",
        ),
        SimpleNamespace(
            role="assistant",
            message="Current assistant response.",
        ),
        SimpleNamespace(
            role="bot",
            message="Legacy bot response.",
        ),
        SimpleNamespace(
            role="agent",
            message="Human employee reply.",
        ),
        SimpleNamespace(
            role="system",
            message="An employee joined the chat.",
        ),
    ]

    summary = generate_handoff_summary(
        "role-test-conversation",
        FakeSession(messages),
    )

    assert summary is not None
    assert summary["message_count"] == 5
    assert summary["user_message_count"] == 1
    assert summary["bot_message_count"] == 2
    assert summary["agent_message_count"] == 1
    assert summary["sentiment"] == "positive"
    assert summary["key_points"].count(
        "👤 Agent assistance provided"
    ) == 1
