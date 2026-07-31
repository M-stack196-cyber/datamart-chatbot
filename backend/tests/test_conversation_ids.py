import asyncio
import inspect
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import String

from app.models.contact_info import ContactInfo
from app.models.conversation_history import ConversationHistory
from app.models.conversation_state import ConversationState
from app.routes import chat as chat_routes
from app.services.lead_agent import LeadCaptureAgent


SUPPORTED_CONVERSATION_IDS = [
    "conv_1785332744215_uzyz8o",
    "9d0c4dd6",
    "6afe8ef4-3b39-45d5-9bc8-3771c32e63d5",
    "internal_1",
]


class QuerySpy:
    def __init__(self, first_result=None, all_result=None):
        self.first_result = first_result
        self.all_result = list(all_result or [])
        self.filter_criteria = []
        self.filter_by_kwargs = []
        self.ordering = []

    def filter(self, *criteria):
        self.filter_criteria.extend(criteria)
        return self

    def filter_by(self, **kwargs):
        self.filter_by_kwargs.append(kwargs)
        return self

    def order_by(self, *ordering):
        self.ordering.extend(ordering)
        return self

    def first(self):
        return self.first_result

    def all(self):
        return self.all_result


class SessionSpy:
    def __init__(self, queries):
        self.queries = queries
        self.queried_models = []
        self.added = []
        self.commit_count = 0
        self.rollback_count = 0
        self.refreshed = []

    def query(self, model):
        self.queried_models.append(model)
        return self.queries[model]

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1

    def refresh(self, value):
        self.refreshed.append(value)


def criterion_values(query):
    values = []

    for criterion in query.filter_criteria:
        right_side = getattr(criterion, "right", None)

        if right_side is not None and hasattr(right_side, "value"):
            values.append(right_side.value)

    return values


def make_state():
    return SimpleNamespace(
        lead_started=False,
        awaiting_field=None,
        collected_data="{}",
        completed_fields="[]",
        optional_attempted="[]",
        skipped_fields="[]",
        mode="bot",
        assigned_agent_id=None,
    )


def test_models_use_consistent_string_conversation_ids():
    for model in (
        ContactInfo,
        ConversationHistory,
        ConversationState,
    ):
        column = model.__table__.c.conversation_id

        assert isinstance(column.type, String)
        assert column.type.length == 50
        assert column.nullable is False

    assert ContactInfo.__table__.c.conversation_id.unique is True
    assert ConversationState.__table__.c.conversation_id.unique is True

    history_targets = {
        foreign_key.target_fullname
        for foreign_key in (
            ConversationHistory.__table__
            .c.conversation_id
            .foreign_keys
        )
    }

    assert history_targets == {
        "contact_info.conversation_id"
    }


@pytest.mark.parametrize(
    "conversation_id",
    SUPPORTED_CONVERSATION_IDS,
)
def test_public_message_polling_preserves_string_ids(
    conversation_id,
):
    message = SimpleNamespace(
        id=8,
        role="assistant",
        message="Test response",
        created_at=datetime.now(timezone.utc),
    )

    query = QuerySpy(all_result=[message])
    session = SessionSpy(
        {ConversationHistory: query}
    )

    result = asyncio.run(
        chat_routes.public_chat_messages(
            conversation_id=conversation_id,
            after_id=7,
            db=session,
        )
    )

    assert result["messages"][0]["id"] == 8
    assert result["messages"][0]["message"] == "Test response"
    assert conversation_id in criterion_values(query)
    assert 7 in criterion_values(query)


@pytest.mark.parametrize(
    "conversation_id",
    SUPPORTED_CONVERSATION_IDS,
)
def test_returning_visitor_history_preserves_string_ids(
    conversation_id,
):
    created_at = datetime.now(timezone.utc)

    message = SimpleNamespace(
        id=1,
        role="user",
        message="Previous message",
        created_at=created_at,
    )

    query = QuerySpy(all_result=[message])
    session = SessionSpy(
        {ConversationHistory: query}
    )

    result = asyncio.run(
        chat_routes.get_chat_history_from_new_tables(
            conversation_id=conversation_id,
            db=session,
        )
    )

    assert result["conversation_id"] == conversation_id
    assert result["messages"][0]["message"] == "Previous message"
    assert result["messages"][0]["timestamp"] == created_at.isoformat()
    assert conversation_id in criterion_values(query)


@pytest.mark.parametrize(
    "conversation_id",
    SUPPORTED_CONVERSATION_IDS,
)
def test_state_loader_preserves_existing_string_ids(
    conversation_id,
):
    state = make_state()
    query = QuerySpy(first_result=state)
    session = SessionSpy(
        {ConversationState: query}
    )

    agent = LeadCaptureAgent(session)
    loaded_state = agent._load_state(conversation_id)

    assert loaded_state is state
    assert conversation_id in criterion_values(query)
    assert session.added == []
    assert session.commit_count == 0


def test_state_loader_creates_internal_string_id():
    query = QuerySpy(first_result=None)
    session = SessionSpy(
        {ConversationState: query}
    )

    agent = LeadCaptureAgent(session)
    state = agent._load_state("internal_1")

    assert state.conversation_id == "internal_1"
    assert state.mode == "bot"
    assert session.added == [state]
    assert session.commit_count == 1
    assert session.refreshed == [state]


class FakeLeadCaptureAgent:
    def __init__(self, db, user=None):
        self.db = db
        self.user = user
        self.mode = "bot"

    def process_message(self, conversation_id, message):
        return "Test response", False


def test_public_chat_generates_full_uuid_string(monkeypatch):
    monkeypatch.setattr(
        chat_routes,
        "LeadCaptureAgent",
        FakeLeadCaptureAgent,
    )

    result = asyncio.run(
        chat_routes.public_chat(
            request=chat_routes.ChatRequest(
                message="Hello",
            ),
            db=object(),
        )
    )

    parsed_id = uuid.UUID(result["conversation_id"])

    assert str(parsed_id) == result["conversation_id"]


def test_public_chat_preserves_supplied_legacy_id(monkeypatch):
    monkeypatch.setattr(
        chat_routes,
        "LeadCaptureAgent",
        FakeLeadCaptureAgent,
    )

    legacy_id = "conv_1785332744215_uzyz8o"

    result = asyncio.run(
        chat_routes.public_chat(
            request=chat_routes.ChatRequest(
                message="Hello",
                conversation_id=legacy_id,
            ),
            db=object(),
        )
    )

    assert result["conversation_id"] == legacy_id


def test_chat_routes_do_not_force_uuid_parsing():
    source = inspect.getsource(chat_routes)

    assert "uuid.UUID(" not in source
    assert "conversation_uuid" not in source
    assert "Invalid conversation ID format" not in source
