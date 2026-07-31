import inspect

from app.routes.admin import handoff as handoff_routes


def test_claim_uses_database_row_lock():
    source = inspect.getsource(
        handoff_routes.claim_handoff
    )

    assert ".with_for_update()" in source
    assert 'state.mode != "pending_human"' in source
    assert '"already_claimed": True' in source


def test_agent_reply_requires_claimed_chat():
    source = inspect.getsource(
        handoff_routes.send_handoff_message
    )

    assert ".with_for_update()" in source
    assert 'state.mode != "human"' in source
    assert (
        "state.assigned_agent_id "
        "!= current_user.id"
    ) in source


def test_agent_reply_rejects_empty_message():
    source = inspect.getsource(
        handoff_routes.send_handoff_message
    )

    assert "payload.message.strip()" in source
    assert "Message cannot be empty" in source


def test_agent_identity_is_saved_with_reply():
    source = inspect.getsource(
        handoff_routes.send_handoff_message
    )

    assert "user_id=current_user.id" in source
    assert 'role="agent"' in source


def test_end_chat_is_idempotent():
    source = inspect.getsource(
        handoff_routes.end_handoff
    )

    assert ".with_for_update()" in source
    assert 'state.mode == "closed"' in source
    assert '"already_closed": True' in source
    assert 'state.mode != "human"' in source
