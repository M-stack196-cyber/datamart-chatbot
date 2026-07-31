from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_WIDGET = (
    REPOSITORY_ROOT /
    "frontend" /
    "public" /
    "dtmindex.html"
)
def widget_content() -> str:
    return PUBLIC_WIDGET.read_text(encoding="utf-8")


def test_widget_has_new_conversation_control():
    content = widget_content()

    assert 'id="datamartNewConversation"' in content
    assert "function startNewConversation()" in content
    assert (
        "newConversationBtn.addEventListener"
        in content
    )


def test_new_conversation_clears_only_browser_state():
    content = widget_content()

    assert (
        "localStorage.removeItem("
        in content
    )
    assert "CONVERSATION_STORAGE_KEY" in content
    assert "conversationId = null;" in content
    assert "lastMessageId = 0;" in content

    # Starting a new topic must not call a delete endpoint.
    assert "deleteConversation" not in content


def test_widget_restores_saved_history():
    content = widget_content()

    assert "function historyUrl(id)" in content
    assert "async function loadChatHistory" in content
    assert "async function restoreConversation" in content
    assert "restoreConversation(savedId);" in content


def test_widget_does_not_end_chat_on_page_unload():
    content = widget_content()

    assert "beforeunload" not in content
    assert "sendBeacon" not in content
    assert "endChatOnUnload" not in content


def test_widget_normalizes_current_and_legacy_ai_roles():
    content = widget_content()

    assert "function normalizeMessageRole(role)" in content
    assert "role === 'assistant'" in content
    assert "role === 'bot'" in content
