import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
import requests
from jinja2 import Environment, FileSystemLoader
from app.models.contact_info import ContactInfo
from app.core.config import settings

class NotificationService:
    """Handles email and Slack notifications for new leads and live handoff requests"""
    
    @staticmethod
    def send_lead_notification(lead: ContactInfo):
        """Send notification for new lead"""
        NotificationService._send_email_notification(lead)
        if settings.SLACK_WEBHOOK_URL:
            NotificationService._send_slack_notification(lead)

    @staticmethod
    def send_handoff_notification(conversation_id, agents: List):
        """Email every online staff member that a visitor wants to talk live.
        `agents` is a list of User objects (already filtered to online staff)."""
        claim_url = f"{settings.APP_URL}/admin/handoff/{conversation_id}"

        for agent in agents:
            try:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = "🔔 Live chat request - a visitor wants to talk now"
                msg['From'] = settings.SMTP_FROM
                msg['To'] = agent.email

                display_name = getattr(agent, "first_name", None) or getattr(agent, "full_name", "there")
                html_content = f"""
                <div style="font-family: Arial, sans-serif; max-width: 480px;">
                    <h2>🔔 Live chat request</h2>
                    <p>Hi {display_name},</p>
                    <p>A visitor on the {settings.COMPANY_NAME} website has asked to speak
                    with a real person right now.</p>
                    <p>
                        <a href="{claim_url}"
                           style="background:#111;color:#fff;padding:10px 18px;
                                  text-decoration:none;border-radius:6px;display:inline-block;">
                            Join the chat
                        </a>
                    </p>
                    <p style="color:#888;font-size:12px;">
                        Whoever claims it first will be connected - the bot has already
                        stopped auto-replying to this visitor.
                    </p>
                </div>
                """
                msg.attach(MIMEText(html_content, 'html'))

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.send_message(msg)
                print(f"✅ Handoff notification sent to {agent.email}")
            except Exception as e:
                print(f"❌ Failed to send handoff notification to {getattr(agent, 'email', '?')}: {e}")
    
    @staticmethod
    def _send_email_notification(lead: ContactInfo):
        """Send email notification to CTO/PMO team"""
        try:
            env = Environment(loader=FileSystemLoader('templates/email'))
            template = env.get_template('lead_notification.html')
            
            html_content = template.render(
                lead=lead,
                company_name=settings.COMPANY_NAME,
                cta_url=f"{settings.APP_URL}/admin/leads/{lead.id}"
            )
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"📢 New Project Inquiry: {lead.project_title or 'Project Inquiry'}"
            msg['From'] = settings.SMTP_FROM
            msg['To'] = settings.NOTIFICATION_EMAIL
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            print(f"✅ Email notification sent for lead #{lead.id}")
        except Exception as e:
            print(f"❌ Failed to send email notification: {e}")
    
    @staticmethod
    def _send_slack_notification(lead: ContactInfo):
        """Send Slack notification for new lead"""
        try:
            message = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "📢 New Project Inquiry",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Name:*\n{lead.name}"},
                            {"type": "mrkdwn", "text": f"*Email:*\n{lead.email}"},
                            {"type": "mrkdwn", "text": f"*Phone:*\n{lead.phone}"},
                            {"type": "mrkdwn", "text": f"*Company:*\n{lead.company or 'N/A'}"}
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Project:*\n{lead.project_title or 'Not specified'}"},
                            {"type": "mrkdwn", "text": f"*Budget:*\n{lead.budget or 'Not decided'}"},
                            {"type": "mrkdwn", "text": f"*Timeline:*\n{lead.timeline or 'Flexible'}"},
                            {"type": "mrkdwn", "text": f"*Industry:*\n{lead.industry or 'N/A'}"}
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Project Description:*\n{lead.project_description[:500]}..."
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "👁️ View in Admin"},
                                "url": f"{settings.APP_URL}/admin/leads/{lead.id}",
                                "style": "primary"
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(settings.SLACK_WEBHOOK_URL, json=message, timeout=5)
            if response.status_code == 200:
                print(f"✅ Slack notification sent for lead #{lead.id}")
            else:
                print(f"❌ Slack notification failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Failed to send Slack notification: {e}")