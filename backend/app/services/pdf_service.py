from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import ChatConversation, ChatMessage
from app.models.conversation_history import ConversationHistory
from app.models.contact_info import ContactInfo


TRANSCRIPT_ROLE_LABELS = {
    "user": "VISITOR",
    "assistant": "BOT",
    "bot": "BOT",
    "agent": "AGENT",
    "system": "SYSTEM",
}


def generate_chat_pdf(conversation_id: str, db: Session):
    """Generate PDF of chat transcript (OLD standalone chat-public flow,
    uses ChatConversation/ChatMessage). Left untouched - still used by
    routes/chat.py's /chat-public/{id}/end."""

    conversation = db.query(ChatConversation).filter(
        ChatConversation.conversation_id == conversation_id
    ).first()

    if not conversation:
        return None

    messages = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation.id
    ).order_by(ChatMessage.timestamp).all()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#D61903'),
        alignment=1
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#333333')
    )

    story = []

    story.append(Paragraph("Datamart Chat Transcript", title_style))
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph(f"<b>Conversation ID:</b> {conversation_id}", styles['Normal']))
    story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    if conversation.visitor_name:
        story.append(Paragraph(f"<b>Visitor:</b> {conversation.visitor_name}", styles['Normal']))
    if conversation.visitor_email:
        story.append(Paragraph(f"<b>Email:</b> {conversation.visitor_email}", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("Chat History", heading_style))
    story.append(Spacer(1, 0.1*inch))

    for msg in messages:
        role_name = TRANSCRIPT_ROLE_LABELS.get(
            msg.role,
            msg.role.upper(),
        )
        time_str = msg.timestamp.strftime("%H:%M")

        msg_text = f"<b>[{role_name}]</b> {time_str}<br/>{msg.message}"
        style = ParagraphStyle(
            'MessageStyle',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            backColor=colors.lightgrey if msg.role == "user" else colors.white,
            borderPadding=5,
            borderRadius=5
        )
        story.append(Paragraph(msg_text, style))
        story.append(Spacer(1, 0.1*inch))

    doc.build(story)
    pdf_content = buffer.getvalue()
    buffer.close()

    return pdf_content


def generate_handoff_pdf(conversation_id: str, db: Session):
    """Generate a PDF transcript for a REAL live-handoff conversation.

    This is the one that matters for production: it reads from
    ConversationHistory (the table every visitor/bot/agent message
    actually gets written to) and ContactInfo (the lead record), not
    the old standalone ChatConversation/ChatMessage tables.

    Called from routes/admin/handoff.py's end_handoff().
    """

    lead = db.query(ContactInfo).filter(
        ContactInfo.conversation_id == conversation_id
    ).first()

    messages = db.query(ConversationHistory).filter(
        ConversationHistory.conversation_id == conversation_id
    ).order_by(ConversationHistory.created_at.asc()).all()

    if not messages:
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#D61903'),
        alignment=1
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#333333')
    )

    story = []

    story.append(Paragraph("Datamart Chat Transcript", title_style))
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph(f"<b>Conversation ID:</b> {conversation_id}", styles['Normal']))
    story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))

    if lead:
        if lead.name and lead.name != "Pending":
            story.append(Paragraph(f"<b>Visitor:</b> {lead.name}", styles['Normal']))
        if lead.email and lead.email != "pending@example.com":
            story.append(Paragraph(f"<b>Email:</b> {lead.email}", styles['Normal']))
        if lead.phone:
            story.append(Paragraph(f"<b>Phone:</b> {lead.phone}", styles['Normal']))
        if lead.project_title:
            story.append(Paragraph(f"<b>Project:</b> {lead.project_title}", styles['Normal']))

    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("Chat History", heading_style))
    story.append(Spacer(1, 0.1*inch))

    for msg in messages:
        role_name = TRANSCRIPT_ROLE_LABELS.get(
            msg.role,
            msg.role.upper(),
        )
        time_str = msg.created_at.strftime("%H:%M") if msg.created_at else ""

        msg_text = f"<b>[{role_name}]</b> {time_str}<br/>{msg.message}"
        style = ParagraphStyle(
            'MessageStyle',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            backColor=colors.lightgrey if msg.role == "user" else colors.white,
            borderPadding=5,
            borderRadius=5
        )
        story.append(Paragraph(msg_text, style))
        story.append(Spacer(1, 0.1*inch))

    doc.build(story)
    pdf_content = buffer.getvalue()
    buffer.close()

    return pdf_content