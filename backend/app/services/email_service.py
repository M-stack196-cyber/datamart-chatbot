import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
from datetime import datetime

def send_chat_email(conversation_id: str, pdf_content: bytes, summary: dict, recipient: str, is_admin: bool = False):
    """Send chat transcript via email with PDF attachment"""
    
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    
    if not smtp_user or not smtp_password:
        print(f"⚠️ Email credentials not configured - would send to {recipient}")
        return False
    
    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = recipient
        msg["Subject"] = f"Chat Transcript - Conversation {conversation_id}"
        
        if is_admin:
            body = f"""
Dear Admin,

A chat conversation has been completed.

Conversation ID: {conversation_id}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Summary:
{summary.get('summary', 'No summary available')}

Key Points:
{', '.join(summary.get('key_points', ['None']))}

Sentiment: {summary.get('sentiment', 'neutral')}

Please find the full chat transcript attached as a PDF.

Best regards,
Datamart Chatbot
"""
        else:
            body = f"""
Dear User,

Thank you for chatting with us! Your conversation has been completed.

Conversation ID: {conversation_id}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

We've attached your chat transcript as a PDF for your records.

If you have any further questions, please don't hesitate to reach out.

Best regards,
Datamart Team
"""
        
        msg.attach(MIMEText(body, "plain"))
        
        pdf_attachment = MIMEApplication(pdf_content, _subtype="pdf")
        pdf_attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=f"chat_transcript_{conversation_id}.pdf"
        )
        msg.attach(pdf_attachment)
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        print(f"✅ Email sent to {recipient}")
        return True
        
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

def send_chat_completion_emails(conversation_id: str, pdf_content: bytes, summary: dict, visitor_email: str):
    """Send email to both admin and user"""
    
    admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
    admin_emails = [email.strip() for email in admin_emails if email.strip()]
    
    if visitor_email:
        send_chat_email(conversation_id, pdf_content, summary, visitor_email, is_admin=False)
    
    for admin_email in admin_emails:
        if admin_email:
            send_chat_email(conversation_id, pdf_content, summary, admin_email, is_admin=True)
