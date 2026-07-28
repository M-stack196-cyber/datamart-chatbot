from sqlalchemy.orm import Session
from app.models import ChatConversation, ChatMessage, ChatSummary
from datetime import datetime

def generate_chat_summary(conversation_id: int, db: Session):
    """Generate summary of chat conversation"""
    
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
