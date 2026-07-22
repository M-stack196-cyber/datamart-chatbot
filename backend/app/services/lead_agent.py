import re
from typing import Dict, Optional, Tuple, Any
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.contact_info import ContactInfo
from app.models.conversation_history import ConversationHistory
from app.models.project_requests import ProjectRequest
from app.schemas.lead import LeadCreate

class LeadCaptureAgent:
    """Smart lead capture agent with optional budget/timeline handling"""
    
    def __init__(self, db: Session, user=None):
        self.db = db
        self.user = user
        self.is_internal = user is not None
        self.collected_data = {}
        self.completed_fields = set()
        self.awaiting_field = None
        self.optional_attempted = set()
        self.skipped_fields = set()
        self.lead_started = False  # Track if lead capture has started
        self._temp_messages = []  # Store messages temporarily for internal users
        
        # Required fields (must collect before saving)
        self.REQUIRED_FIELDS = {
            "name": {
                "prompt": "What's your full name?",
                "required": True,
                "validation": lambda x: len(x.split()) >= 2,
                "error": "Please provide your full name (first and last)."
            },
            "email": {
                "prompt": "What's your email address?",
                "required": True,
                "validation": lambda x: bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', x)),
                "error": "Please provide a valid email address (e.g., name@domain.com)."
            },
            "phone": {
                "prompt": "What's the best phone number to reach you?",
                "required": True,
                "validation": lambda x: len(re.sub(r'[\s\-\(\)\+]', '', x)) >= 7,
                "error": "Please provide a valid phone number (at least 7 digits)."
            },
            "project_description": {
                "prompt": "Could you describe your project in detail?",
                "required": True,
                "validation": lambda x: len(x) >= 10,
                "error": "Please provide more details about your project (at least 10 characters)."
            }
        }
        
        # Optional fields
        self.OPTIONAL_FIELDS = {
            "budget": {
                "prompt": "Do you have an estimated budget in mind? (Optional - you can say 'not decided')",
                "follow_up": "That's fine! We can discuss budget later.",
                "parse": self._parse_budget,
                "skip_phrases": ["not decided", "don't know", "not sure", "not yet", "skip", "none", "later", "flexible"],
                "default": "Not decided"
            },
            "timeline": {
                "prompt": "Do you have a preferred timeline for this project? (Optional - you can say 'flexible')",
                "follow_up": "Perfect! I've recorded everything.",
                "parse": self._parse_timeline,
                "skip_phrases": ["flexible", "not decided", "don't know", "not sure", "not yet", "skip", "none", "later"],
                "default": "Flexible"
            },
            "company": {
                "prompt": "What company do you work for? (Optional)",
                "follow_up": "Got it!",
                "parse": lambda x: {"value": x.strip()},
                "skip_phrases": ["none", "not", "n/a", "no company", "skip"],
                "default": None
            },
            "project_title": {
                "prompt": "Would you like to give your project a title? (Optional)",
                "follow_up": "Nice!",
                "parse": lambda x: {"value": x.strip()},
                "skip_phrases": ["no", "skip", "none", "not"],
                "default": None
            }
        }
    
    def _parse_budget(self, value: str) -> Dict[str, Any]:
        """Parse budget value and return a dict with 'value' key."""
        value = value.lower().strip()
        skip_phrases = ["not decided", "don't know", "not sure", "no idea", "flexible", "later", "skip"]
        
        if any(phrase in value for phrase in skip_phrases):
            return {"value": "Not decided"}
        
        patterns = [
            r'\$?\s*(\d+[.,]?\d*)\s*(k|thousand|million|m|billion|b)?',
            r'(\d+[.,]?\d*)\s*(k|thousand|million|m|billion|b)?\s*dollars?',
            r'around\s*\$?\s*(\d+[.,]?\d*)\s*(k|thousand|million)?',
            r'less than\s*\$?\s*(\d+[.,]?\d*)\s*(k|thousand|million)?',
            r'more than\s*\$?\s*(\d+[.,]?\d*)\s*(k|thousand|million)?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, value, re.IGNORECASE)
            if match:
                num = float(match.group(1).replace(',', ''))
                unit = match.group(2) if len(match.groups()) > 1 else ''
                
                if unit in ['k', 'thousand']:
                    num *= 1000
                elif unit in ['m', 'million']:
                    num *= 1000000
                elif unit in ['b', 'billion']:
                    num *= 1000000000
                
                return {"value": f"${num:,.0f}"}
        
        if len(value) > 2 and not any(p in value for p in skip_phrases):
            return {"value": value}
        
        return {"value": "Not decided"}
    
    def _parse_timeline(self, value: str) -> Dict[str, Any]:
        """Parse timeline value and return a dict with 'value' key."""
        value = value.lower().strip()
        flexible_phrases = ["flexible", "not decided", "don't know", "not sure", "no idea", "later", "asap"]
        
        if any(phrase in value for phrase in flexible_phrases):
            return {"value": "Flexible"}
        
        patterns = [
            r'(\d+)\s*(?:week|wk)s?',
            r'(\d+)\s*(?:month|mo)s?',
            r'(\d+)\s*(?:quarter|qtr)s?',
            r'(\d+)\s*(?:year|yr)s?',
            r'(q[1-4])\s*\d{4}',
            r'([a-z]+)\s+\d{4}',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, value, re.IGNORECASE)
            if match:
                return {"value": value}
        
        common = {
            'asap': 'Immediate (ASAP)',
            'immediate': 'Immediate (ASAP)',
            'yesterday': 'Immediate (ASAP)',
            'soon': 'Within 1 month',
            'next week': 'Within 1 week',
            'next month': 'Within 1 month',
            'next quarter': 'Within 3 months',
            'end of year': 'End of current year'
        }
        
        for key, val in common.items():
            if key in value:
                return {"value": val}
        
        if len(value) > 2:
            return {"value": value}
        
        return {"value": "Flexible"}
    
    def classify_intent(self, message: str) -> str:
        """Classify user intent as project inquiry or general inquiry."""
        message_lower = message.lower()
        
        # Check if it's a question about services, pricing, or general info
        service_keywords = [
            "services", "offer", "provide", "do you", "can you", 
            "how much", "cost", "pricing", "price", "budget",
            "timeline", "timing", "when", "how long",
            "staff augmentation", "mvp", "saas", "ai", "cloud",
            "development", "custom software", "maintenance"
        ]
        
        for keyword in service_keywords:
            if keyword in message_lower:
                return "project_inquiry"
        
        # Check for project-related keywords
        project_keywords = [
            "build", "develop", "create", "make", "project", "app", "website",
            "software", "system", "platform", "solution", "mvp", "product",
            "want to build", "looking for", "need help with", "hire", "developers",
            "i need", "i want", "help with"
        ]
        
        for keyword in project_keywords:
            if keyword in message_lower:
                return "project_inquiry"
        
        return "general_inquiry"
    
    def get_service_response(self, message: str) -> Optional[str]:
        """Generate direct response for service-related questions."""
        message_lower = message.lower()
        
        services_info = {
            "services": """### Datamart Services

Datamart offers the following services:

🤝 **Staff Augmentation**: Pre-vetted senior engineers at 50-70% lower cost. Placed in 1-2 weeks.

🚀 **MVP Development**: Launch your product in 8-12 weeks with our expert team.

⚡ **SaaS Maintenance**: 99.99% uptime guarantee with 24/7 support and monitoring.

🤖 **AI Automation**: Agentic AI, LLMs, and RAG solutions for your business.

💻 **Custom Software**: Full-stack development with React, Node.js, Python, and more.

☁️ **Cloud & DevOps**: AWS, Docker, Kubernetes - scalable and secure infrastructure.

Would you like to learn more about any of these services or start a project request?""",
            
            "cost": """### Staff Augmentation Pricing

💰 **Cost Savings**: 50-70% lower cost than US hiring

💵 **No Recruiting Fees**: We don't charge placement fees

📋 **No Benefits Overhead**: You only pay for engineering time

🔄 **Flexible Monthly Contracts**: Scale up or down as needed

For a custom quote, please start a project request and our team will get back to you within 24-48 hours.""",
            
            "timeline": """### Engagement Timeline

⏱️ **Time to Hire**: 1-2 weeks to place engineers

🚀 **MVP Launch**: 8-12 weeks from kickoff

📅 **Flexible Contracts**: Month-to-month or project-based

🔧 **24/7 Support**: Available for all active projects

Would you like to discuss your specific timeline requirements?""",
            
            "staff augmentation": """### Staff Augmentation

👨‍💻 **Pre-vetted Senior Engineers**: Access to a global talent pool

🌍 **Global Delivery**: US-managed, globally delivered

🔄 **Seamless Integration**: Engineers report to you and use your tools

💸 **50-70% Lower Cost**: Compared to US hiring

📋 **No Recruiting Fees**: Save on placement costs

Would you like to discuss your specific staffing needs?"""
        }
        
        # Check for matching keywords
        for key, response in services_info.items():
            if key in message_lower:
                return response
        
        # Check for general "what", "how", "why" questions
        if message_lower.startswith(("what", "how", "why", "when", "who", "where")):
            return """### General Information

I'd be happy to help you learn more about Datamart! Here are the key areas I can assist with:

• **Services**: Staff Augmentation, MVP Development, SaaS Maintenance, AI Automation, Custom Software, Cloud & DevOps
• **Cost**: 50-70% lower cost than US hiring, no recruiting fees
• **Timeline**: 1-2 weeks to hire, 8-12 weeks for MVP launch
• **Team**: US-managed, globally delivered

What specific information would you like to know about?"""
        
        return None
    
    def extract_field_value(self, field: str, message: str) -> Optional[str]:
        message = message.strip()
        
        if field == "email":
            pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            match = re.search(pattern, message)
            return match.group(0) if match else None
        
        elif field == "phone":
            cleaned = re.sub(r'[\s\-\(\)\+]', '', message)
            if len(cleaned) >= 7:
                return message
            return None
        
        elif field == "name":
            words = message.split()
            if len(words) >= 2 and all(len(w) >= 2 for w in words):
                return " ".join(words[:3])
            return None
        
        elif field == "project_description":
            if len(message) > 10:
                return message
            return None
        
        elif len(message) > 1:
            return message
        
        return None
    
    def should_skip_field(self, field: str, message: str) -> bool:
        if field not in self.OPTIONAL_FIELDS:
            return False
        skip_phrases = self.OPTIONAL_FIELDS[field].get("skip_phrases", [])
        message_lower = message.lower().strip()
        return any(phrase in message_lower for phrase in skip_phrases)
    
    def get_next_question(self) -> Optional[Tuple[str, str]]:
        for field, config in self.REQUIRED_FIELDS.items():
            if field not in self.completed_fields:
                self.awaiting_field = field
                return (field, config["prompt"])
        
        for field, config in self.OPTIONAL_FIELDS.items():
            if field not in self.completed_fields and field not in self.optional_attempted:
                self.optional_attempted.add(field)
                self.awaiting_field = field
                return (field, config["prompt"])
        
        self.awaiting_field = None
        return None
    
    def process_message(self, conversation_id: UUID, message: str) -> Tuple[Optional[str], bool]:
        # Save user message (handles missing contact_info gracefully)
        self._save_message(conversation_id, "user", message)
        
        response = None
        lead_complete = False
        
        # Check for direct service response first
        service_response = self.get_service_response(message)
        if service_response and not self.lead_started:
            # Return service info without starting lead capture
            self._save_message(conversation_id, "assistant", service_response)
            return service_response, False
        
        if self.awaiting_field:
            field = self.awaiting_field
            is_optional = field in self.OPTIONAL_FIELDS
            
            if is_optional and self.should_skip_field(field, message):
                default = self.OPTIONAL_FIELDS[field].get("default", "Not specified")
                self.collected_data[field] = default
                self.completed_fields.add(field)
                self.skipped_fields.add(field)
                
                next_q = self.get_next_question()
                if next_q:
                    field_name, prompt = next_q
                    response = f"I understand. {prompt}"
                else:
                    response = self._generate_completion_message()
                    lead_complete = True
                    self._save_lead(conversation_id)
            else:
                value = self.extract_field_value(field, message)
                
                if value and self._validate_field(field, value):
                    if is_optional:
                        parser = self.OPTIONAL_FIELDS[field].get("parse")
                        if parser:
                            parsed = parser(value)
                            self.collected_data[field] = parsed.get("value", value)
                        else:
                            self.collected_data[field] = value
                    else:
                        self.collected_data[field] = value
                    
                    self.completed_fields.add(field)
                    
                    next_q = self.get_next_question()
                    if next_q:
                        field_name, prompt = next_q
                        response = f"Great! {prompt}"
                    else:
                        response = self._generate_completion_message()
                        lead_complete = True
                        self._save_lead(conversation_id)
                else:
                    config = self.REQUIRED_FIELDS.get(field, {})
                    error_msg = config.get("error", "Please provide that information.")
                    response = f"{error_msg}"
        else:
            intent = self.classify_intent(message)
            
            if intent == "project_inquiry" and not self.lead_started:
                # Start lead capture only if not already started
                self.lead_started = True
                self.collected_data = {}
                self.completed_fields = set()
                self.optional_attempted = set()
                self.skipped_fields = set()
                self.awaiting_field = None
                
                if self.is_internal:
                    self.collected_data["name"] = self.user.full_name
                    self.collected_data["email"] = self.user.email
                    self.completed_fields.add("name")
                    self.completed_fields.add("email")
                    
                    next_q = self.get_next_question()
                    if next_q:
                        field_name, prompt = next_q
                        response = f"Hi {self.user.first_name}! I'd be happy to help you submit a project request. {prompt}"
                else:
                    next_q = self.get_next_question()
                    if next_q:
                        field_name, prompt = next_q
                        response = f"Great! I'd love to learn more about your project. {prompt}"
            else:
                # Fallback for general inquiries
                response = "I'm here to help! You can ask me about our services, pricing, timeline, or start a project request. What would you like to know?"
        
        if response:
            self._save_message(conversation_id, "assistant", response)
        
        return response, lead_complete
    
    def _validate_field(self, field: str, value: str) -> bool:
        config = self.REQUIRED_FIELDS.get(field)
        if config and "validation" in config:
            return config["validation"](value)
        return True
    
    def _generate_completion_message(self) -> str:
        name = self.collected_data.get('name', 'N/A')
        project_title = self.collected_data.get('project_title', 'your project')
        budget = self.collected_data.get('budget', 'Not decided')
        timeline = self.collected_data.get('timeline', 'Flexible')
        
        if self.is_internal:
            return f"""✅ **Project Request Submitted Successfully!**

📋 **Summary:**
• Project: {project_title}
• Budget: {budget}
• Timeline: {timeline}
• Department: {self.collected_data.get('department', 'Not specified')}

📌 **Next Steps:**
Our PMO team will review your request and get back to you within 48 hours.

Would you like to track the status of your request?"""
        else:
            return f"""✅ **Perfect! I've recorded your project details:**

📋 **Summary:**
• Name: {name}
• Email: {self.collected_data.get('email', 'N/A')}
• Phone: {self.collected_data.get('phone', 'N/A')}
• Project: {project_title}
• Budget: {budget}
• Timeline: {timeline}
• Company: {self.collected_data.get('company', 'Not specified')}

📌 **Next Steps:**
Our CTO/PMO team will review your project and reach out within 24-48 hours.

Is there anything else I can help you with?"""
    
    def _save_lead(self, conversation_id: UUID):
        """Save lead - updates existing record instead of inserting duplicate"""
        try:
            print(f"📝 Saving lead for conversation: {conversation_id}")
            
            if self.is_internal:
                request = ProjectRequest(
                    user_id=self.user.id,
                    project_title=self.collected_data.get('project_title', 'Untitled Project'),
                    project_description=self.collected_data.get('project_description', ''),
                    budget=self.collected_data.get('budget'),
                    timeline=self.collected_data.get('timeline'),
                    priority=self.collected_data.get('priority', 'medium'),
                    department=self.collected_data.get('department'),
                    is_urgent=self.collected_data.get('priority', '').lower() == 'high',
                    status='pending'
                )
                self.db.add(request)
                self.db.commit()
                self.db.refresh(request)
            else:
                # Check if a ContactInfo record already exists for this conversation
                existing_lead = self.db.query(ContactInfo).filter_by(
                    conversation_id=conversation_id
                ).first()
                
                if existing_lead:
                    # UPDATE existing record (FIX: Don't insert duplicate!)
                    print(f"🔄 Updating existing lead for conversation: {conversation_id}")
                    existing_lead.name = self.collected_data.get('name', '')
                    existing_lead.email = self.collected_data.get('email', '')
                    existing_lead.phone = self.collected_data.get('phone', '')
                    existing_lead.project_description = self.collected_data.get('project_description', '')
                    existing_lead.company = self.collected_data.get('company')
                    existing_lead.country = self.collected_data.get('country')
                    existing_lead.project_title = self.collected_data.get('project_title')
                    existing_lead.industry = self.collected_data.get('industry')
                    existing_lead.budget = self.collected_data.get('budget', 'Not decided')
                    existing_lead.timeline = self.collected_data.get('timeline', 'Flexible')
                    existing_lead.preferred_contact_method = self.collected_data.get('preferred_contact_method')
                    existing_lead.source = 'public_widget'
                    existing_lead.status = 'new'
                    existing_lead.lead_score = 0
                    
                    self.db.commit()
                    self.db.refresh(existing_lead)
                    print(f"✅ Lead updated successfully with ID: {existing_lead.id}")
                else:
                    # INSERT new record (only if it doesn't exist)
                    print(f"🆕 Creating new lead for conversation: {conversation_id}")
                    lead = ContactInfo(
                        conversation_id=conversation_id,
                        name=self.collected_data.get('name', ''),
                        email=self.collected_data.get('email', ''),
                        phone=self.collected_data.get('phone', ''),
                        project_description=self.collected_data.get('project_description', ''),
                        company=self.collected_data.get('company'),
                        country=self.collected_data.get('country'),
                        project_title=self.collected_data.get('project_title'),
                        industry=self.collected_data.get('industry'),
                        budget=self.collected_data.get('budget', 'Not decided'),
                        timeline=self.collected_data.get('timeline', 'Flexible'),
                        preferred_contact_method=self.collected_data.get('preferred_contact_method'),
                        source='public_widget',
                        status='new',
                        lead_score=0
                    )
                    self.db.add(lead)
                    self.db.commit()
                    self.db.refresh(lead)
                    print(f"✅ Lead saved successfully with ID: {lead.id}")
            
            # Reset the agent state after saving
            self.lead_started = False
            self.awaiting_field = None
            
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error saving lead: {e}")
            import traceback
            traceback.print_exc()
            # Don't raise - let the conversation continue
    
    def _save_message(self, conversation_id: UUID, role: str, message: str):
        """Save message - handles missing contact_info gracefully"""
        if self.is_internal:
            self._temp_messages.append({"role": role, "message": message})
        else:
            try:
                # First check if contact_info exists
                contact = self.db.query(ContactInfo).filter_by(
                    conversation_id=conversation_id
                ).first()
                
                if not contact:
                    # Create a minimal contact record if it doesn't exist
                    lead = ContactInfo(
                        conversation_id=conversation_id,
                        name="Pending",
                        email="pending@example.com",
                        phone="0000000000",
                        project_description="Project details being collected..."
                    )
                    self.db.add(lead)
                    self.db.commit()
                    self.db.refresh(lead)
                    print(f"✅ Created minimal contact for conversation: {conversation_id}")
                
                # Now save the message
                msg = ConversationHistory(
                    conversation_id=conversation_id,
                    role=role,
                    message=message
                )
                self.db.add(msg)
                self.db.commit()
                
            except Exception as e:
                # Rollback and log error
                self.db.rollback()
                print(f"❌ Error saving message: {e}")
                # Don't raise - let the conversation continue