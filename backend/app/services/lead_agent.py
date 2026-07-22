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
        project_keywords = [
            "build", "develop", "create", "make", "project", "app", "website",
            "software", "system", "platform", "solution", "mvp", "product",
            "want to build", "looking for", "need help with", "hire", "developers",
            "i need", "i want", "can you"
        ]
        message_lower = message.lower()
        for keyword in project_keywords:
            if keyword in message_lower:
                return "project_inquiry"
        return "general_inquiry"
    
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
        self._save_message(conversation_id, "user", message)
        
        response = None
        lead_complete = False
        
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
                response = None
        
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
                preferred_contact_method=self.collected_data.get('preferred_contact_method')
            )
            self.db.add(lead)
            self.db.commit()
            self.db.refresh(lead)
        
        # Reset the agent state after saving
        self.lead_started = False
        self.awaiting_field = None
    
    def _save_message(self, conversation_id: UUID, role: str, message: str):
        if self.is_internal:
            if not hasattr(self, '_temp_messages'):
                self._temp_messages = []
            self._temp_messages.append({"role": role, "message": message})
        else:
            msg = ConversationHistory(
                conversation_id=conversation_id,
                role=role,
                message=message
            )
            self.db.add(msg)
            self.db.commit()