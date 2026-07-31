import asyncio
import inspect
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import inspect as sqlalchemy_inspect

from app.models import (
    ChatConversation,
    ChatMessage,
    Conversation,
    Message,
    User,
)
from app.routes import chat as chat_routes


class QueryStub:
    def __init__(
        self,
        *,
        first_result=None,
        count_result=0,
    ):
        self.first_result = first_result
        self.count_result = count_result
        self.filter_criteria = []

    def filter(self, *criteria):
        self.filter_criteria.extend(criteria)
        return self

    def first(self):
        return self.first_result

    def count(self):
        return self.count_result


class SessionStub:
    def __init__(
        self,
        *,
        conversation=None,
        message_count=0,
        fail_commit=False,
    ):
        self.conversation_query = QueryStub(
            first_result=conversation,
        )
        self.message_query = QueryStub(
            count_result=message_count,
        )
        self.queried_models = []
        self.added = []
        self.commit_count = 0
        self.rollback_count = 0
        self.fail_commit = fail_commit

    def query(self, model):
        self.queried_models.append(model)

        if model is Conversation:
            return self.conversation_query

        if model is Message:
            return self.message_query

        raise AssertionError(
            f"Unexpected queried model: {model}"
        )

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commit_count += 1

        if self.fail_commit:
            raise RuntimeError("Simulated commit failure")

    def rollback(self):
        self.rollback_count += 1


def criterion_values(query):
    values = []

    for criterion in query.filter_criteria:
        right_side = getattr(criterion, "right", None)

        if (
            right_side is not None
            and hasattr(right_side, "value")
        ):
            values.append(right_side.value)

    return values


class FakeLeadCaptureAgent:
    calls = []

    def __init__(self, db, user=None):
        self.db = db
        self.user = user

    def process_message(
        self,
        conversation_id,
        message,
    ):
        self.__class__.calls.append(
            {
                "conversation_id": conversation_id,
                "message": message,
            }
        )
        return "Assistant reply", False


def make_user(user_id=7):
    return SimpleNamespace(
        id=user_id,
        full_name="Test User",
        email="test@example.com",
        role="customer",
    )


def test_authenticated_models_map_to_correct_tables():
    assert Conversation.__tablename__ == "conversations"
    assert Message.__tablename__ == "messages"

    assert (
        ChatConversation.__tablename__
        == "chat_conversations"
    )
    assert ChatMessage.__tablename__ == "chat_messages"

    message_fk = next(
        iter(
            Message.__table__
            .c.conversation_id
            .foreign_keys
        )
    )

    assert (
        message_fk.target_fullname
        == "conversations.id"
    )

    user_relationships = sqlalchemy_inspect(
        User
    ).relationships

    assert "conversations" in user_relationships
    assert "chat_conversations" in user_relationships


def test_app_chat_saves_each_turn_exactly_once(
    monkeypatch,
):
    FakeLeadCaptureAgent.calls = []

    monkeypatch.setattr(
        chat_routes,
        "LeadCaptureAgent",
        FakeLeadCaptureAgent,
    )

    conversation = SimpleNamespace(
        id=42,
        user_id=7,
        title="New conversation",
        updated_at=None,
    )

    session = SessionStub(
        conversation=conversation,
        message_count=0,
    )

    result = asyncio.run(
        chat_routes.app_chat(
            request=(
                chat_routes.AuthenticatedChatRequest(
                    message="How can Datamart help me?",
                    conversation_id=42,
                )
            ),
            current_user=make_user(7),
            db=session,
        )
    )

    assert result["response"] == "Assistant reply"
    assert result["conversation_id"] == 42

    assert FakeLeadCaptureAgent.calls == [
        {
            "conversation_id": "internal_7_42",
            "message": "How can Datamart help me?",
        }
    ]

    assert criterion_values(
        session.conversation_query
    ) == [42, 7]

    assert session.queried_models == [
        Conversation,
        Message,
    ]

    assert len(session.added) == 2
    assert all(
        isinstance(value, Message)
        for value in session.added
    )
    assert not any(
        isinstance(value, ChatMessage)
        for value in session.added
    )

    user_message, assistant_message = session.added

    assert user_message.conversation_id == 42
    assert user_message.role == "user"
    assert (
        user_message.content
        == "How can Datamart help me?"
    )

    assert assistant_message.conversation_id == 42
    assert assistant_message.role == "assistant"
    assert assistant_message.content == "Assistant reply"

    assert (
        conversation.title
        == "How can Datamart help me?"
    )
    assert conversation.updated_at is not None

    assert session.commit_count == 1
    assert session.rollback_count == 0


def test_app_chat_rejects_another_users_conversation(
    monkeypatch,
):
    class UnexpectedAgent:
        def __init__(self, *args, **kwargs):
            raise AssertionError(
                "Agent must not run for unauthorized chat"
            )

    monkeypatch.setattr(
        chat_routes,
        "LeadCaptureAgent",
        UnexpectedAgent,
    )

    session = SessionStub(conversation=None)

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            chat_routes.app_chat(
                request=(
                    chat_routes
                    .AuthenticatedChatRequest(
                        message="Unauthorized message",
                        conversation_id=99,
                    )
                ),
                current_user=make_user(7),
                db=session,
            )
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Conversation not found"

    assert criterion_values(
        session.conversation_query
    ) == [99, 7]

    assert session.added == []
    assert session.commit_count == 0
    assert session.rollback_count == 0


def test_app_chat_rolls_back_message_commit(
    monkeypatch,
):
    FakeLeadCaptureAgent.calls = []

    monkeypatch.setattr(
        chat_routes,
        "LeadCaptureAgent",
        FakeLeadCaptureAgent,
    )

    conversation = SimpleNamespace(
        id=42,
        user_id=7,
        title="Existing title",
        updated_at=None,
    )

    session = SessionStub(
        conversation=conversation,
        message_count=2,
        fail_commit=True,
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated commit failure",
    ):
        asyncio.run(
            chat_routes.app_chat(
                request=(
                    chat_routes
                    .AuthenticatedChatRequest(
                        message="Another question",
                        conversation_id=42,
                    )
                ),
                current_user=make_user(7),
                db=session,
            )
        )

    assert session.commit_count == 1
    assert session.rollback_count == 1
    assert conversation.title == "Existing title"


def test_app_chat_has_no_legacy_message_writes():
    source = inspect.getsource(chat_routes.app_chat)

    assert "ChatConversation" not in source
    assert "ChatMessage" not in source
    assert "chat_messages" not in source


def test_chat_page_passes_selected_conversation_once():
    repository_root = (
        Path(__file__).resolve().parents[2]
    )

    source = (
        repository_root
        / "frontend"
        / "src"
        / "pages"
        / "ChatPage.jsx"
    ).read_text(encoding="utf-8")

    assert re.search(
        r"api\.chat\(\s*question,\s*"
        r"conversationId,\s*\)",
        source,
    )

    assert "api.saveMessage(" not in source
