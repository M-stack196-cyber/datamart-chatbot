import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from jinja2 import Environment, FileSystemLoader
from app.models.contact_info import ContactInfo
from app.core.config import settings

class NotificationService:
    """Handles email and Slack notifications for new leads"""
    
    @staticmethod
    async def send_lead_notification(lead: ContactInfo):
        """Send notification for new lead"""
        await NotificationService._send_email_notification(lead)
        if settings.SLACK_WEBHOOK_URL:
            await NotificationService._send_slack_notification(lead)
    
    @staticmethod
    async def _send_email_notification(lead: ContactInfo):
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
            
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            print(f"✅ Email notification sent for lead #{lead.id}")
        except Exception as e:
            print(f"❌ Failed to send email notification: {e}")
    
    @staticmethod
    async def _send_slack_notification(lead: ContactInfo):
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