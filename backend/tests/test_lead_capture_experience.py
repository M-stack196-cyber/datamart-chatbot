from app.services.lead_agent import LeadCaptureAgent


class DummySession:
    """Database placeholder for tests that replace persistence methods."""
    pass


def make_agent():
    agent = LeadCaptureAgent(DummySession())
    saved_messages = []

    # Keep these unit tests focused on conversation behavior rather than
    # database persistence.
    agent._load_state = lambda conversation_id: None
    agent._save_state = lambda: None
    agent._save_message = (
        lambda conversation_id, role, message:
        saved_messages.append(
            {
                "conversation_id": conversation_id,
                "role": role,
                "message": message,
            }
        )
    )

    return agent, saved_messages


def test_known_question_is_answered_and_pending_field_resumes():
    agent, saved_messages = make_agent()

    agent.lead_started = True
    agent.awaiting_field = "email"
    agent.collected_data = {"name": "John Doe"}
    agent.completed_fields = {"name"}

    response, complete = agent.process_message(
        "conversation-1",
        "How long does a website normally take?",
    )

    assert complete is False
    assert response is not None
    assert "To continue your project request" in response
    assert "What's your email address?" in response
    assert agent.awaiting_field == "email"
    assert "email" not in agent.completed_fields

    assistant_messages = [
        item
        for item in saved_messages
        if item["role"] == "assistant"
    ]

    assert len(assistant_messages) == 1


def test_unknown_question_uses_rag_without_consuming_pending_field():
    agent, saved_messages = make_agent()

    agent.lead_started = True
    agent.awaiting_field = "email"
    agent.collected_data = {"name": "John Doe"}
    agent.completed_fields = {"name"}

    response, complete = agent.process_message(
        "conversation-2",
        "Do you integrate Stripe subscriptions?",
    )

    assert response is None
    assert complete is False
    assert agent.interruption_detected is True
    assert (
        agent.interruption_resume_prompt
        == "What's your email address?"
    )
    assert agent.awaiting_field == "email"
    assert "email" not in agent.completed_fields

    # Only the visitor message is stored here. The route stores the RAG
    # assistant response after generating it.
    assert len(saved_messages) == 1
    assert saved_messages[0]["role"] == "user"


def test_optional_phone_can_be_skipped():
    agent, _ = make_agent()

    agent.lead_started = True
    agent.awaiting_field = "phone"
    agent.collected_data = {
        "name": "John Doe",
        "email": "john@example.com",
    }
    agent.completed_fields = {"name", "email"}

    response, complete = agent.process_message(
        "conversation-3",
        "skip",
    )

    assert complete is False
    assert agent.collected_data["phone"] == ""
    assert "phone" in agent.completed_fields
    assert "phone" in agent.skipped_fields
    assert agent.awaiting_field == "project_description"
    assert "describe your project" in response.lower()


def test_handoff_collects_name_and_email_then_continues_automatically():
    agent, saved_messages = make_agent()
    handoff_calls = []

    def start_handoff(conversation_id):
        handoff_calls.append(conversation_id)
        agent.mode = "pending_human"
        return "Connecting you with a team member now."

    agent._start_handoff = start_handoff

    first_response, _ = agent.process_message(
        "conversation-4",
        "I want to talk to a human",
    )

    assert "contact details" in first_response
    assert "full name" in first_response
    assert agent.awaiting_field == "name"
    assert agent.collected_data["_handoff_requested"] is True
    assert handoff_calls == []

    second_response, _ = agent.process_message(
        "conversation-4",
        "John Doe",
    )

    assert "email address" in second_response
    assert agent.awaiting_field == "email"
    assert agent.collected_data["name"] == "John Doe"
    assert handoff_calls == []

    third_response, _ = agent.process_message(
        "conversation-4",
        "john@example.com",
    )

    assert third_response == "Connecting you with a team member now."
    assert agent.mode == "pending_human"
    assert agent.collected_data["email"] == "john@example.com"
    assert "_handoff_requested" not in agent.collected_data
    assert handoff_calls == ["conversation-4"]

    assistant_messages = [
        item
        for item in saved_messages
        if item["role"] == "assistant"
    ]

    assert len(assistant_messages) == 3


def test_new_project_preserves_verified_contact_details():
    agent, _ = make_agent()

    agent.collected_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1 555 123 4567",
        "old_project_description": "Old project",
    }
    agent.completed_fields = {
        "name",
        "email",
        "phone",
        "project_description",
    }

    response, complete = agent.process_message(
        "conversation-5",
        "I want to build a new website",
    )

    assert complete is False
    assert agent.collected_data == {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1 555 123 4567",
    }
    assert agent.completed_fields == {
        "name",
        "email",
        "phone",
    }
    assert agent.awaiting_field == "project_description"
    assert "describe your project" in response.lower()

def test_phone_requires_real_digits():
    agent, _ = make_agent()

    assert (
        agent.extract_field_value(
            "phone",
            "This is definitely not my phone number",
        )
        is None
    )

    assert (
        agent._validate_field(
            "phone",
            "This is definitely not my phone number",
        )
        is False
    )


def test_valid_phone_number_is_accepted():
    agent, _ = make_agent()

    phone = "+1 (555) 123-4567"

    assert agent.extract_field_value("phone", phone) == phone
    assert agent._validate_field("phone", phone) is True

