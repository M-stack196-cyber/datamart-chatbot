from sqlalchemy.orm import Session
from app.models import ChatConversation, ChatMessage, ChatSummary
from app.models.conversation_history import ConversationHistory
from datetime import datetime


def generate_chat_summary(conversation_id: int, db: Session):
    """Generate summary of chat conversation (OLD standalone chat-public
    flow, uses ChatMessage/ChatSummary). Left untouched - still used by
    routes/chat.py's /chat-public/{id}/end."""

    messages = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation_id
    ).order_by(ChatMessage.timestamp).all()

    if len(messages) == 0:
        return None

    key_points = []
    user_messages = []
    bot_messages = []

    for msg in messages:
        if msg.role == "user":
            user_messages.append(msg.message)
            msg_lower = msg.message.lower()
            if "budget" in msg_lower or "cost" in msg_lower or "price" in msg_lower:
                key_points.append("💰 Budget/Cost discussed")
            if "timeline" in msg_lower or "time" in msg_lower or "deadline" in msg_lower:
                key_points.append("⏰ Timeline discussed")
            if "project" in msg_lower or "build" in msg_lower or "create" in msg_lower:
                key_points.append("📋 Project requirements discussed")
            if "service" in msg_lower or "offer" in msg_lower:
                key_points.append("💼 Services discussed")
        elif msg.role == "bot":
            bot_messages.append(msg.message)
        elif msg.role == "agent":
            key_points.append("👤 Agent assistance provided")

    sentiment = "neutral"
    positive_words = ["good", "great", "excellent", "happy", "satisfied", "perfect", "love"]
    negative_words = ["bad", "poor", "slow", "expensive", "issue", "problem", "delay"]

    all_text = " ".join(user_messages + bot_messages).lower()
    positive_count = sum(1 for word in positive_words if word in all_text)
    negative_count = sum(1 for word in negative_words if word in all_text)

    if positive_count > negative_count:
        sentiment = "positive"
    elif negative_count > positive_count:
        sentiment = "negative"

    summary_text = f"""
Chat Conversation Summary
=========================
Total Messages: {len(messages)}
User Messages: {len(user_messages)}
Bot Responses: {len(bot_messages)}
Key Topics: {', '.join(key_points) if key_points else 'General conversation'}
Sentiment: {sentiment.upper()}
"""

    existing_summary = db.query(ChatSummary).filter(
        ChatSummary.conversation_id == conversation_id
    ).first()

    if existing_summary:
        existing_summary.summary = summary_text
        existing_summary.key_points = ",".join(key_points)
        existing_summary.sentiment = sentiment
    else:
        chat_summary = ChatSummary(
            conversation_id=conversation_id,
            summary=summary_text,
            key_points=",".join(key_points),
            sentiment=sentiment
        )
        db.add(chat_summary)

    db.commit()

    return {
        "summary": summary_text,
        "key_points": key_points,
        "sentiment": sentiment,
        "message_count": len(messages),
        "user_message_count": len(user_messages),
        "bot_message_count": len(bot_messages)
    }


def generate_handoff_summary(conversation_id: str, db: Session):
    """Generate a summary for a REAL live-handoff conversation.

    Reads from ConversationHistory (what every visitor/bot/agent message
    actually gets written to). This is NOT persisted to a table yet - it's
    computed on demand. That's fine for "email it when the chat ends", but
    if we later want it to show instantly on the admin panel without
    recomputing, we'll want a ChatSummary-style table keyed by
    conversation_id (UUID) instead of the int-only one the old flow uses.

    Called from routes/admin/handoff.py's end_handoff(), and can also be
    called directly from an admin-panel endpoint to show the summary on
    demand for an active/past conversation.
    """

    messages = db.query(ConversationHistory).filter(
        ConversationHistory.conversation_id == conversation_id
    ).order_by(ConversationHistory.created_at.asc()).all()

    if len(messages) == 0:
        return None

    key_points = []
    user_messages = []
    bot_messages = []
    agent_messages = []

    for msg in messages:
        if msg.role == "user":
            user_messages.append(msg.message)
            msg_lower = msg.message.lower()
            if "budget" in msg_lower or "cost" in msg_lower or "price" in msg_lower:
                key_points.append("💰 Budget/Cost discussed")
            if "timeline" in msg_lower or "time" in msg_lower or "deadline" in msg_lower:
                key_points.append("⏰ Timeline discussed")
            if "project" in msg_lower or "build" in msg_lower or "create" in msg_lower:
                key_points.append("📋 Project requirements discussed")
            if "service" in msg_lower or "offer" in msg_lower:
                key_points.append("💼 Services discussed")
        elif msg.role == "bot":
            bot_messages.append(msg.message)
        elif msg.role == "agent":
            agent_messages.append(msg.message)
            key_points.append("👤 Agent assistance provided")

    sentiment = "neutral"
    positive_words = ["good", "great", "excellent", "happy", "satisfied", "perfect", "love"]
    negative_words = ["bad", "poor", "slow", "expensive", "issue", "problem", "delay"]

    all_text = " ".join(user_messages + bot_messages).lower()
    positive_count = sum(1 for word in positive_words if word in all_text)
    negative_count = sum(1 for word in negative_words if word in all_text)

    if positive_count > negative_count:
        sentiment = "positive"
    elif negative_count > positive_count:
        sentiment = "negative"

    # de-dupe key points while keeping order (e.g. multiple agent replies
    # shouldn't repeat "Agent assistance provided" N times)
    key_points = list(dict.fromkeys(key_points))

    summary_text = f"""
Chat Conversation Summary
=========================
Total Messages: {len(messages)}
Visitor Messages: {len(user_messages)}
Bot Responses: {len(bot_messages)}
Agent Replies: {len(agent_messages)}
Key Topics: {', '.join(key_points) if key_points else 'General conversation'}
Sentiment: {sentiment.upper()}
"""

    return {
        "summary": summary_text,
        "key_points": key_points,
        "sentiment": sentiment,
        "message_count": len(messages),
        "user_message_count": len(user_messages),
        "bot_message_count": len(bot_messages),
        "agent_message_count": len(agent_messages),
    }