import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from supabase import create_client
from openai import OpenAI
import resend
from config import get_settings

class EmailService:
    """Service for email generation, sending, and management"""
    
    def __init__(self, test_mode: bool = False):
        self.settings = get_settings()
        self.test_mode = test_mode  # Add test mode flag
        self.supabase = create_client(
            self.settings.SUPABASE_URL,
            self.settings.SUPABASE_SERVICE_ROLE_KEY
        )
        
        # Initialize OpenAI for email generation
        if self.settings.OPENAI_API_KEY:
            self.openai_client = OpenAI(
                api_key=self.settings.OPENAI_API_KEY
            )
        
        # Initialize Resend for email sending (only if not in test mode)
        if self.settings.RESEND_API_KEY and not self.test_mode:
            resend.api_key = self.settings.RESEND_API_KEY
    
    async def generate_email(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personalized email using AI or templates"""
        try:
            lead_name = params.get("leadName", "")
            lead_company = params.get("leadCompany", "")
            lead_title = params.get("leadTitle", "")
            email_type = params.get("emailType", "cold_outreach")
            tone = params.get("tone", "professional")
            custom_context = params.get("customContext", "")
            template_id = params.get("templateId")
            lead_data = params.get("leadData", {})
            
            if not lead_name:
                return {
                    "status": "error",
                    "message": "Lead name is required"
                }
            
            # If template_id is provided, use template-based generation
            if template_id:
                return await self._generate_email_with_template(template_id, lead_name, lead_company, lead_title, lead_data)
            
            # Otherwise, use AI generation
            prompt = self._create_email_prompt(lead_name, lead_company, lead_title, email_type, tone, custom_context)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-5-nano-2025-08-07",
                messages=[
                    {"role": "system", "content": "You are an expert email copywriter specializing in B2B outreach."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000
            )
            
            email_content = response.choices[0].message.content.strip()
            
            # Parse subject and body
            lines = email_content.split('\n')
            subject = ""
            body = ""
            
            for i, line in enumerate(lines):
                if line.lower().startswith('subject:'):
                    subject = line[8:].strip()
                    body = '\n'.join(lines[i+1:]).strip()
                    break
            
            if not subject:
                # If no subject line found, use first line as subject
                subject = lines[0] if lines else "Follow up"
                body = '\n'.join(lines[1:]).strip() if len(lines) > 1 else email_content
            
            return {
                "status": "success",
                "data": {
                    "subject": subject,
                    "body": body,
                    "generatedAt": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _generate_email_with_template(self, template_id: str, lead_name: str, lead_company: str, lead_title: str, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate email using a template and AI personalization"""
        try:
            # Get the template
            template_response = self.supabase.table("email_templates").select("*").eq("id", template_id).execute()
            
            if not template_response.data:
                return {
                    "status": "error",
                    "message": "Template not found"
                }
            
            template = template_response.data[0]
            template_subject = template.get("subject", "")
            template_body = template.get("body", "")
            persona = template.get("persona", "professional")
            stage = template.get("stage", "initial")
            
            # Create personalization prompt
            personalization_prompt = f"""
            You are an expert email copywriter. Personalize the following email template for a specific lead.
            
            Template Subject: {template_subject}
            Template Body: {template_body}
            
            Lead Information:
            - Name: {lead_name}
            - Company: {lead_company}
            - Title: {lead_title}
            - Persona: {persona}
            - Stage: {stage}
            
            Additional Lead Data: {json.dumps(lead_data) if lead_data else 'None'}
            
            Instructions:
            1. Personalize the subject line and body for this specific lead
            2. Replace any placeholders with actual lead information
            3. Maintain the original tone and structure of the template
            4. Make it feel natural and personalized, not templated
            5. Return ONLY the personalized subject and body in this exact JSON format:
            {{
                "subject": "personalized subject here",
                "body": "personalized body here"
            }}
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-5-nano-2025-08-07",
                messages=[
                    {"role": "system", "content": "You are an expert email copywriter. Return only valid JSON."},
                    {"role": "user", "content": personalization_prompt}
                ]
            )
            
            # Parse the AI response
            ai_content = response.choices[0].message.content.strip()
            
            # Try to parse JSON response
            try:
                email_data = json.loads(ai_content)
                return {
                    "status": "success",
                    "data": {
                        "subject": email_data.get("subject", template_subject),
                        "body": email_data.get("body", template_body),
                        "templateId": template_id,
                        "persona": persona,
                        "stage": stage
                    }
                }
            except json.JSONDecodeError:
                # Fallback: use template as-is with basic personalization
                personalized_subject = template_subject.replace("{lead_name}", lead_name).replace("{company}", lead_company or "")
                personalized_body = template_body.replace("{lead_name}", lead_name).replace("{company}", lead_company or "").replace("{title}", lead_title or "")
                
                return {
                    "status": "success",
                    "data": {
                        "subject": personalized_subject,
                        "body": personalized_body,
                        "templateId": template_id,
                        "persona": persona,
                        "stage": stage
                    }
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Template generation failed: {str(e)}"
            }
    
    async def create_draft(self, user_id: str, draft_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create email draft for a user"""
        try:
            draft = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "lead_id": draft_data.get("leadId"),
                "subject": draft_data.get("subject"),
                "body": draft_data.get("body"),
                "status": "draft",
                "persona": draft_data.get("persona"),
                "stage": draft_data.get("stage"),
                "created_at": datetime.now().isoformat()
            }
            
            response = self.supabase.table("email_drafts").insert(draft).execute()
            
            return {
                "status": "success",
                "data": response.data[0]
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def send_draft(self, draft_id: str) -> Dict[str, Any]:
        """Send email draft"""
        try:
            # Get draft
            draft_response = self.supabase.table("email_drafts").select("*").eq("id", draft_id).execute()
            if not draft_response.data:
                return {
                    "status": "error",
                    "message": "Draft not found"
                }
            
            draft = draft_response.data[0]
            
            # Get lead info
            lead_response = self.supabase.table("leads").select("*").eq("id", draft["lead_id"]).execute()
            if not lead_response.data:
                return {
                    "status": "error",
                    "message": "Lead not found"
                }
            
            lead = lead_response.data[0]
            
            # Send email using Resend
            if self.settings.RESEND_API_KEY:
                email_params = {
                    "from": self.settings.FROM_EMAIL,
                    "to": [lead["email"]],
                    "subject": draft["subject"],
                    "html": self._format_email_html(draft["body"])
                }
                
                email_response = resend.Emails.send(email_params)
                
                # Update draft status
                self.supabase.table("email_drafts").update({
                    "status": "sent",
                    "sent_at": datetime.now().isoformat()
                }).eq("id", draft_id).execute()
                
                return {
                    "status": "success",
                    "message": "Email sent successfully",
                    "email_id": email_response.get("id")
                }
            else:
                return {
                    "status": "error",
                    "message": "Email service not configured"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def create_campaign(self, user_id: str, name: str, description: str = None, template_id: str = None, 
                             selected_leads: List[str] = None, email_interval: int = 24, 
                             daily_limit: int = 50, send_time_start: str = "07:00", 
                             send_time_end: str = "09:00", timezone: str = "America/New_York", 
                             scheduled_at: datetime = None) -> Dict[str, Any]:
        """Create email campaign with scheduling parameters for a user"""
        try:
            # Fetch template data to get subject and body
            subject = ""
            body = ""
            print(f"DEBUG: Creating campaign with template_id: {template_id}")
            if template_id:
                template_result = self.supabase.table("email_templates").select("subject, body").eq("id", template_id).execute()
                print(f"DEBUG: Template query result: {template_result.data}")
                if template_result.data:
                    template = template_result.data[0]
                    subject = template.get("subject", "")
                    body = template.get("body", "")
                    print(f"DEBUG: Found template - subject: '{subject}', body length: {len(body)}")
                else:
                    print(f"DEBUG: No template found for id: {template_id}")
            else:
                print("DEBUG: No template_id provided")
            
            campaign = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "name": name,
                "subject": subject,
                "body": body,
                "description": description,
                "template_id": template_id,
                "selected_leads": selected_leads or [],
                "email_interval": email_interval,
                "daily_limit": daily_limit,
                "send_time_start": send_time_start,
                "send_time_end": send_time_end,
                "timezone": timezone,
                "status": "draft",
                "total_leads": len(selected_leads) if selected_leads else 0,
                "sent_count": 0,
                "scheduled_count": 0,
                "open_rate": 0.0,
                "reply_rate": 0.0,
                "created_at": datetime.now().isoformat(),
                "scheduled_at": scheduled_at.isoformat() if scheduled_at else None
            }
            
            print(f"DEBUG: Campaign data before insert - subject: '{campaign['subject']}', body length: {len(campaign['body'])}")
            response = self.supabase.table("email_campaigns").insert(campaign).execute()
            print(f"DEBUG: Insert response: {response}")
            
            return {
                "status": "success",
                "data": response.data[0]
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def start_campaign(self, user_id: str, campaign_id: str) -> Dict[str, Any]:
        """Start email campaign for a user with proper scheduling"""
        try:
            # Get campaign details
            campaign_result = self.supabase.table("email_campaigns").select("*").eq("id", campaign_id).eq("user_id", user_id).execute()
            
            if not campaign_result.data:
                return {
                    "status": "error",
                    "message": "Campaign not found"
                }
            
            campaign = campaign_result.data[0]
            
            # Update campaign status - handle missing columns gracefully
            try:
                self.supabase.table("email_campaigns").update({
                    "status": "active",
                    "started_at": datetime.now().isoformat()
                }).eq("id", campaign_id).eq("user_id", user_id).execute()
            except Exception as db_error:
                # If started_at column doesn't exist, just update status
                if "started_at" in str(db_error):
                    self.supabase.table("email_campaigns").update({
                        "status": "active"
                    }).eq("id", campaign_id).eq("user_id", user_id).execute()
                else:
                    raise db_error
            
            # Schedule first batch of emails
            await self._schedule_campaign_emails(campaign)
            
            return {
                "status": "success",
                "message": "Campaign started and emails scheduled successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _schedule_campaign_emails(self, campaign: Dict[str, Any]) -> None:
        """Schedule emails for a campaign based on interval and time constraints"""
        try:
            from datetime import datetime, timedelta
            import pytz
            
            # Get campaign parameters
            selected_leads = campaign.get("selected_leads", [])
            email_interval = campaign.get("email_interval", 24)  # hours
            daily_limit = campaign.get("daily_limit", 50)
            send_time_start = campaign.get("send_time_start", "07:00")
            send_time_end = campaign.get("send_time_end", "09:00")
            timezone_str = campaign.get("timezone", "America/New_York")
            template_id = campaign.get("template_id")
            
            if not selected_leads or not template_id:
                return
            
            # Get timezone
            try:
                tz = pytz.timezone(timezone_str)
            except:
                tz = pytz.timezone("UTC")
            
            # Get template details
            template_result = self.supabase.table("email_templates").select("*").eq("id", template_id).execute()
            if not template_result.data:
                return
            
            template = template_result.data[0]
            
            # Get lead details
            leads_result = self.supabase.table("leads").select("*").in_("id", selected_leads).execute()
            leads = leads_result.data or []
            
            # Calculate send times
            now = datetime.now(tz)
            current_date = now.date()
            
            # Parse send time window
            start_hour, start_minute = map(int, send_time_start.split(":"))
            end_hour, end_minute = map(int, send_time_end.split(":"))
            
            scheduled_count = 0
            current_day_count = 0
            current_send_time = now
            
            # Schedule emails for each lead
            for i, lead in enumerate(leads):
                if not lead.get("email"):
                    continue
                
                # Check daily limit
                if current_day_count >= daily_limit:
                    # Move to next day
                    current_date += timedelta(days=1)
                    current_day_count = 0
                    current_send_time = tz.localize(datetime.combine(current_date, datetime.min.time().replace(hour=start_hour, minute=start_minute)))
                
                # Ensure send time is within the allowed window
                send_date = current_send_time.date()
                send_time_start_today = tz.localize(datetime.combine(send_date, datetime.min.time().replace(hour=start_hour, minute=start_minute)))
                send_time_end_today = tz.localize(datetime.combine(send_date, datetime.min.time().replace(hour=end_hour, minute=end_minute)))
                
                if current_send_time < send_time_start_today:
                    current_send_time = send_time_start_today
                elif current_send_time > send_time_end_today:
                    # Move to next day
                    current_date += timedelta(days=1)
                    current_day_count = 0
                    current_send_time = tz.localize(datetime.combine(current_date, datetime.min.time().replace(hour=start_hour, minute=start_minute)))
                
                # Create scheduled email record
                scheduled_email = {
                    "id": str(uuid.uuid4()),
                    "campaign_id": campaign["id"],
                    "lead_id": lead["id"],
                    "to_email": lead["email"],
                    "subject": template["subject"],
                    "body": template["body"],
                    "scheduled_at": current_send_time.isoformat(),
                    "status": "scheduled",
                    "created_at": datetime.now().isoformat()
                }
                
                # Insert into scheduled_emails table - handle missing table gracefully
                try:
                    self.supabase.table("scheduled_emails").insert(scheduled_email).execute()
                except Exception as db_error:
                    # If scheduled_emails table doesn't exist, skip scheduling for now
                    if "scheduled_emails" in str(db_error):
                        print(f"Warning: scheduled_emails table not found, skipping email scheduling")
                        break
                    else:
                        raise db_error
                
                scheduled_count += 1
                current_day_count += 1
                
                # Add interval for next email
                current_send_time += timedelta(hours=email_interval)
            
            # Update campaign with scheduled count
            self.supabase.table("email_campaigns").update({
                "scheduled_count": scheduled_count
            }).eq("id", campaign["id"]).execute()
            
        except Exception as e:
            print(f"Error scheduling campaign emails: {e}")
    
    async def process_scheduled_emails(self) -> Dict[str, Any]:
        """Process scheduled emails that are due to be sent"""
        try:
            from datetime import datetime
            
            # Get scheduled emails that are due - use system timezone
            now = datetime.now().isoformat()
            print(f"[DEBUG] Current system time: {now}")
            
            scheduled_result = self.supabase.table("scheduled_emails").select("*").eq("status", "scheduled").lte("scheduled_at", now).execute()
            
            scheduled_emails = scheduled_result.data or []
            print(f"[DEBUG] Found {len(scheduled_emails)} scheduled emails due for sending")
            
            # Debug: Show scheduled times for comparison
            for email in scheduled_emails[:3]:  # Show first 3 for debugging
                print(f"[DEBUG] Email {email['id'][:8]}... scheduled for: {email['scheduled_at']}")
            sent_count = 0
            failed_count = 0
            
            for scheduled_email in scheduled_emails:
                try:
                    # Send the email via Resend
                    email_params = {
                        "to": scheduled_email["to_email"],
                        "subject": scheduled_email["subject"],
                        "body": scheduled_email["body"],
                        "leadId": scheduled_email["lead_id"]
                    }
                    
                    result = await self.send_email(email_params)
                    
                    if result["status"] == "success":
                        # Update scheduled email status
                        self.supabase.table("scheduled_emails").update({
                            "status": "sent",
                            "sent_at": datetime.now().isoformat(),
                            "resend_id": result.get("data", {}).get("id")
                        }).eq("id", scheduled_email["id"]).execute()
                        
                        sent_count += 1
                    else:
                        # Mark as failed
                        self.supabase.table("scheduled_emails").update({
                            "status": "failed",
                            "error_message": result.get("message", "Unknown error"),
                            "failed_at": datetime.now().isoformat()
                        }).eq("id", scheduled_email["id"]).execute()
                        
                        failed_count += 1
                        
                except Exception as e:
                    # Mark as failed
                    self.supabase.table("scheduled_emails").update({
                        "status": "failed",
                        "error_message": str(e),
                        "failed_at": datetime.now().isoformat()
                    }).eq("id", scheduled_email["id"]).execute()
                    
                    failed_count += 1
                    print(f"Failed to send scheduled email {scheduled_email['id']}: {e}")
            
            return {
                "status": "success",
                "message": f"Processed {len(scheduled_emails)} scheduled emails: {sent_count} sent, {failed_count} failed",
                "data": {
                    "processed": len(scheduled_emails),
                    "sent": sent_count,
                    "failed": failed_count
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing scheduled emails: {str(e)}"
            }
    
    async def pause_campaign(self, user_id: str, campaign_id: str) -> Dict[str, Any]:
        """Pause email campaign for a user"""
        try:
            # Update campaign status - handle missing columns gracefully
            try:
                self.supabase.table("email_campaigns").update({
                    "status": "paused",
                    "paused_at": datetime.now().isoformat()
                }).eq("id", campaign_id).eq("user_id", user_id).execute()
            except Exception as db_error:
                # If paused_at column doesn't exist, just update status
                if "paused_at" in str(db_error):
                    self.supabase.table("email_campaigns").update({
                        "status": "paused"
                    }).eq("id", campaign_id).eq("user_id", user_id).execute()
                else:
                    raise db_error
            
            return {
                "status": "success",
                "message": "Campaign paused successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def resume_campaign(self, user_id: str, campaign_id: str) -> Dict[str, Any]:
        """Resume paused email campaign for a user"""
        try:
            # Update campaign status - handle missing columns gracefully
            try:
                self.supabase.table("email_campaigns").update({
                    "status": "active",
                    "resumed_at": datetime.now().isoformat()
                }).eq("id", campaign_id).eq("user_id", user_id).execute()
            except Exception as db_error:
                # If resumed_at column doesn't exist, just update status
                if "resumed_at" in str(db_error):
                    self.supabase.table("email_campaigns").update({
                        "status": "active"
                    }).eq("id", campaign_id).eq("user_id", user_id).execute()
                else:
                    raise db_error
            
            return {
                "status": "success",
                "message": "Campaign resumed successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def delete_campaign(self, user_id: str, campaign_id: str) -> Dict[str, Any]:
        """Delete email campaign for a user"""
        try:
            print(f"[DELETE_CAMPAIGN] Attempting to delete campaign {campaign_id} for user {user_id}")
            
            # First check if campaign exists
            campaign_response = self.supabase.table("email_campaigns").select("id").eq("id", campaign_id).eq("user_id", user_id).execute()
            print(f"[DELETE_CAMPAIGN] Campaign check response: {campaign_response.data}")
            
            if not campaign_response.data:
                print(f"[DELETE_CAMPAIGN] Campaign not found")
                return {
                    "status": "error",
                    "message": "Campaign not found"
                }
            
            # Delete campaign
            delete_response = self.supabase.table("email_campaigns").delete().eq("id", campaign_id).eq("user_id", user_id).execute()
            print(f"[DELETE_CAMPAIGN] Delete response: {delete_response}")
            
            return {
                "status": "success",
                "message": "Campaign deleted successfully"
            }
        except Exception as e:
            print(f"[DELETE_CAMPAIGN] Error: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def generate_template(self, persona: str, stage: str, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate email template using AI"""
        try:
            if not self.openai_client:
                return {
                    "status": "error",
                    "message": "OpenAI API key not configured"
                }
            
            prompt = f"""
            Generate a professional email template for:
            Persona: {persona}
            Stage: {stage}
            Lead Data: {lead_data}
            
            Return a JSON with 'subject' and 'body' fields.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-5-nano-2025-08-07",
                messages=[
                    {"role": "system", "content": "You are an expert email copywriter."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.choices[0].message.content
            import json
            email_data = json.loads(content)
            
            return {
                "status": "success",
                "data": email_data
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def use_template(self, template_id: str) -> Dict[str, Any]:
        """Use an existing template"""
        try:
            response = self.supabase.table("email_templates").select("*").eq("id", template_id).execute()
            if response.data:
                return {
                    "status": "success",
                    "data": response.data[0]
                }
            else:
                return {
                    "status": "error",
                    "message": "Template not found"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
            

    
    def _create_email_prompt(self, lead_name: str, lead_company: str, lead_title: str, 
                           email_type: str, tone: str, custom_context: str) -> str:
        """Create email generation prompt"""
        base_prompt = f"""
Generate a personalized {email_type} email with the following details:

Recipient: {lead_name}
Company: {lead_company}
Job Title: {lead_title}
Tone: {tone}
"""
        
        if custom_context:
            base_prompt += f"\nAdditional Context: {custom_context}"
        
        if email_type == "cold_outreach":
            base_prompt += """

Email Guidelines:
- Keep it concise (under 150 words)
- Start with a personalized opener
- Clearly state the value proposition
- Include a soft call-to-action
- Professional but conversational tone
- No aggressive sales language

Format:
Subject: [compelling subject line]
[email body]
"""
        elif email_type == "follow_up":
            base_prompt += """

Email Guidelines:
- Reference previous interaction
- Provide additional value
- Gentle reminder of previous conversation
- Clear next steps

Format:
Subject: [follow-up subject line]
[email body]
"""
        elif email_type == "meeting_request":
            base_prompt += """

Email Guidelines:
- Specific meeting purpose
- Suggest 2-3 time options
- Brief agenda outline
- Easy to say yes

Format:
Subject: [meeting request subject]
[email body]
"""
        
        return base_prompt
    
    async def send_email(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send email using Resend or log in test mode"""
        try:
            to_email = params.get("to")
            subject = params.get("subject")
            body = params.get("body")
            lead_id = params.get("leadId")
            from_email = params.get("from", self.settings.FROM_EMAIL)
            
            if not all([to_email, subject, body]):
                return {
                    "status": "error",
                    "message": "Missing required email parameters"
                }
            
            # Test mode: Log email instead of sending
            if self.test_mode:
                print(f"\n=== TEST MODE EMAIL ===")
                print(f"From: {from_email}")
                print(f"To: {to_email}")
                print(f"Subject: {subject}")
                print(f"Body: {body[:200]}...")
                print(f"Lead ID: {lead_id}")
                print(f"========================\n")
                
                # Create a mock response for test mode
                mock_resend_id = f"test_{uuid.uuid4().hex[:8]}"
            else:
                # Send email via Resend
                email_data = {
                    "from": from_email,
                    "to": [to_email],
                    "subject": subject,
                    "html": self._format_email_html(body),
                    "text": body
                }
                
                response = resend.Emails.send(email_data)
                mock_resend_id = response.get("id")
            
            # Save email to database
            email_record = {
                "id": str(uuid.uuid4()),
                "lead_id": lead_id,
                "to_email": to_email,
                "from_email": from_email,
                "subject": subject,
                "body": body,
                "status": "sent" if not self.test_mode else "test_sent",
                "sent_at": datetime.now().isoformat(),
                "resend_id": mock_resend_id,
                "created_at": datetime.now().isoformat(),
                "test_mode": self.test_mode
            }
            
            self.supabase.table("emails").insert(email_record).execute()
            
            # Update lead email status
            if lead_id:
                self.supabase.table("leads").update({
                    "email_status": "sent" if not self.test_mode else "test_sent",
                    "last_contacted": datetime.now().isoformat()
                }).eq("id", lead_id).execute()
            
            return {
                "status": "success",
                "message": f"Email {'logged (test mode)' if self.test_mode else 'sent successfully'}",
                "data": {
                    "emailId": email_record["id"],
                    "resendId": mock_resend_id,
                    "testMode": self.test_mode
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Email {'logging' if self.test_mode else 'sending'} failed: {str(e)}"
            }
    
    def _format_email_html(self, body: str) -> str:
        """Format plain text email body as HTML"""
        # Convert line breaks to HTML
        html_body = body.replace('\n', '<br>\n')
        
        # Wrap in basic HTML structure
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        {html_body}
    </div>
</body>
</html>
"""
    
    async def get_email_templates(self, user_id: str) -> Dict[str, Any]:
        """Get all email templates for a user"""
        try:
            response = self.supabase.table("email_templates").select("*").eq("user_id", user_id).execute()
            return {
                "status": "success",
                "data": response.data,
                "count": len(response.data)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "data": []
            }
    
    async def save_template(self, user_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """Save email template for a user"""
        try:
            template_data = {
                "user_id": user_id,
                "subject": request.get("subject"),
                "body": request.get("body"),
                "persona": request.get("persona"),
                "stage": request.get("stage"),
                "created_at": datetime.now().isoformat()
            }
            response = self.supabase.table("email_templates").insert(template_data).execute()
            return {
                "status": "success",
                "data": response.data[0]
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def update_email_template(self, user_id: str, template_id: str, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update email template for a user"""
        try:
            template_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("email_templates").update(template_data).eq("id", template_id).eq("user_id", user_id).execute()
            
            return {
                "status": "success",
                "message": "Template updated successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error updating template: {str(e)}"
            }
    
    async def delete_email_template(self, user_id: str, template_id: str) -> Dict[str, Any]:
        """Delete email template for a user"""
        try:
            result = self.supabase.table("email_templates").delete().eq("id", template_id).eq("user_id", user_id).execute()
            
            return {
                "status": "success",
                "message": "Template deleted successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error deleting template: {str(e)}"
            }
    
    async def delete_template(self, user_id: str, template_id: str) -> Dict[str, Any]:
        """Delete email template (alias method)"""
        return await self.delete_email_template(user_id, template_id)
    
    async def get_email_drafts(self, user_id: str = None) -> Dict[str, Any]:
        """Get email drafts for a user"""
        try:
            query = self.supabase.table("email_drafts").select("*")
            if user_id:
                query = query.eq("user_id", user_id)
            
            response = query.execute()
            return {
                "status": "success",
                "data": response.data,
                "count": len(response.data)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "data": []
            }
    
    async def save_email_draft(self, draft_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save email draft"""
        try:
            draft = {
                "id": str(uuid.uuid4()),
                "lead_id": draft_data.get("leadId"),
                "subject": draft_data.get("subject"),
                "body": draft_data.get("body"),
                "status": draft_data.get("status", "draft"),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            result = self.supabase.table("email_drafts").insert(draft).execute()
            
            return {
                "status": "success",
                "message": "Draft saved successfully",
                "data": draft
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error saving draft: {str(e)}"
            }
    
    async def update_email_draft(self, user_id: str, draft_id: str, draft_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update email draft for a user"""
        try:
            draft_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("email_drafts").update(draft_data).eq("id", draft_id).eq("user_id", user_id).execute()
            
            return {
                "status": "success",
                "message": "Draft updated successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error updating draft: {str(e)}"
            }
    
    async def delete_email_draft(self, user_id: str, draft_id: str) -> Dict[str, Any]:
        """Delete email draft for a user"""
        try:
            result = self.supabase.table("email_drafts").delete().eq("id", draft_id).eq("user_id", user_id).execute()
            
            return {
                "status": "success",
                "message": "Draft deleted successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error deleting draft: {str(e)}"
            }
    
    async def create_email_campaign(self, user_id: str, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create email campaign for a user"""
        try:
            # Fetch template data to get subject and body if templateId is provided
            subject = campaign_data.get("subject", "")
            body = campaign_data.get("body", "")
            template_id = campaign_data.get("templateId")
            
            if template_id and not subject:
                template_result = self.supabase.table("email_templates").select("subject, body").eq("id", template_id).execute()
                if template_result.data:
                    template = template_result.data[0]
                    subject = template.get("subject", "")
                    body = template.get("body", "")
            
            campaign = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "name": campaign_data.get("name"),
                "subject": subject,
                "body": body,
                "lead_ids": campaign_data.get("leadIds", []),
                "status": "draft",
                "scheduled_at": campaign_data.get("scheduledAt"),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            result = self.supabase.table("email_campaigns").insert(campaign).execute()
            
            return {
                "status": "success",
                "message": "Campaign created successfully",
                "data": campaign
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error creating campaign: {str(e)}"
            }
    
    async def get_email_campaigns(self, user_id: str) -> Dict[str, Any]:
        """Get email campaigns for a user"""
        try:
            result = self.supabase.table("email_campaigns").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            
            campaigns = result.data or []
            for campaign in campaigns:
                campaign_id = campaign.get('id')
                
                # Calculate actual metrics from database
                # Get scheduled emails count
                try:
                    scheduled_result = self.supabase.table("scheduled_emails").select("*").eq("campaign_id", campaign_id).execute()
                    scheduled_emails = scheduled_result.data or []
                    scheduled_count = len([e for e in scheduled_emails if e.get('status') == 'scheduled'])
                    sent_count = len([e for e in scheduled_emails if e.get('status') == 'sent'])
                except Exception:
                    # If scheduled_emails table doesn't exist, use database values or defaults
                    scheduled_count = campaign.get('scheduled_count', 0)
                    sent_count = campaign.get('sent_count', 0)
                
                # Get email events for this campaign
                try:
                    events_result = self.supabase.table("email_events").select("*").eq("campaign_id", campaign_id).execute()
                    events = events_result.data or []
                    
                    # Calculate metrics from events
                    sent_events = [e for e in events if e.get("event_type") == "sent"]
                    opened_events = [e for e in events if e.get("event_type") == "opened"]
                    replied_events = [e for e in events if e.get("event_type") == "replied"]
                    
                    # Update sent count from events if available
                    if sent_events:
                        sent_count = len(sent_events)
                    
                    # Calculate rates
                    open_rate = (len(opened_events) / sent_count * 100) if sent_count > 0 else 0.0
                    reply_rate = (len(replied_events) / sent_count * 100) if sent_count > 0 else 0.0
                    
                except Exception:
                    # If email_events table doesn't exist, use database values or defaults
                    open_rate = campaign.get('open_rate', 0.0)
                    reply_rate = campaign.get('reply_rate', 0.0)
                
                # Calculate total leads from selected_leads
                selected_leads = campaign.get('selected_leads', [])
                total_leads = len(selected_leads) if isinstance(selected_leads, list) else 0
                
                # Update campaign with calculated values (using camelCase for frontend compatibility)
                campaign['sentCount'] = sent_count
                campaign['scheduledCount'] = scheduled_count
                campaign['totalLeads'] = total_leads
                campaign['openRate'] = round(open_rate, 2)
                campaign['replyRate'] = round(reply_rate, 2)
                
                # Also keep snake_case for database compatibility
                campaign['sent_count'] = sent_count
                campaign['scheduled_count'] = scheduled_count
                campaign['total_leads'] = total_leads
                campaign['open_rate'] = round(open_rate, 2)
                campaign['reply_rate'] = round(reply_rate, 2)
                
                # Ensure all expected fields exist with default values (both snake_case and camelCase)
                campaign.setdefault('email_interval', 24)
                campaign.setdefault('daily_limit', 50)
                campaign.setdefault('send_time_start', '07:00')
                campaign.setdefault('send_time_end', '09:00')
                campaign.setdefault('timezone', 'America/New_York')
                
                # Add camelCase versions for frontend compatibility
                campaign['emailInterval'] = campaign.get('email_interval', 24)
                campaign['dailyLimit'] = campaign.get('daily_limit', 50)
                campaign['sendTimeStart'] = campaign.get('send_time_start', '07:00')
                campaign['sendTimeEnd'] = campaign.get('send_time_end', '09:00')
                
                # Get template subject for display
                if campaign.get('template_id'):
                    try:
                        template_result = self.supabase.table("email_templates").select("subject").eq("id", campaign['template_id']).execute()
                        if template_result.data:
                            campaign['templateSubject'] = template_result.data[0].get('subject', 'Unknown Template')
                        else:
                            campaign['templateSubject'] = 'Unknown Template'
                    except:
                        campaign['templateSubject'] = 'Unknown Template'
                else:
                    campaign['templateSubject'] = 'No Template'
            
            return {
                "status": "success",
                "data": campaigns
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error fetching campaigns: {str(e)}"
            }
    
    async def send_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Send email campaign"""
        try:
            # Get campaign details
            campaign_result = self.supabase.table("email_campaigns").select("*").eq("id", campaign_id).execute()
            
            if not campaign_result.data:
                return {
                    "status": "error",
                    "message": "Campaign not found"
                }
            
            campaign = campaign_result.data[0]
            lead_ids = campaign.get("lead_ids", [])
            
            if not lead_ids:
                return {
                    "status": "error",
                    "message": "No leads in campaign"
                }
            
            # Get lead details
            leads_result = self.supabase.table("leads").select("*").in_("id", lead_ids).execute()
            leads = leads_result.data or []
            
            sent_count = 0
            failed_count = 0
            
            # Send emails to each lead
            for lead in leads:
                try:
                    email_params = {
                        "to": lead.get("email"),
                        "subject": campaign["subject"],
                        "body": campaign["body"],
                        "leadId": lead["id"]
                    }
                    
                    result = await self.send_email(email_params)
                    
                    if result["status"] == "success":
                        sent_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    failed_count += 1
                    print(f"Failed to send email to {lead.get('email')}: {e}")
            
            # Update campaign status
            self.supabase.table("email_campaigns").update({
                "status": "sent",
                "sent_at": datetime.now().isoformat(),
                "sent_count": sent_count,
                "failed_count": failed_count
            }).eq("id", campaign_id).execute()
            
            return {
                "status": "success",
                "message": f"Campaign sent: {sent_count} successful, {failed_count} failed",
                "data": {
                    "sentCount": sent_count,
                    "failedCount": failed_count
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error sending campaign: {str(e)}"
            }
    
    async def get_email_metrics(self, user_id: str, time_range: str = "30d") -> Dict[str, Any]:
        """Get email metrics for a user"""
        try:
            # Calculate date range
            now = datetime.now()
            if time_range == "7d":
                start_date = now - timedelta(days=7)
            elif time_range == "30d":
                start_date = now - timedelta(days=30)
            elif time_range == "90d":
                start_date = now - timedelta(days=90)
            else:
                start_date = now - timedelta(days=30)
            
            # Fetch email events in date range for the user
            events_result = self.supabase.table("email_events").select("*").eq("user_id", user_id).gte("created_at", start_date.isoformat()).execute()
            events = events_result.data or []
            
            # Calculate metrics from events
            sent_events = [e for e in events if e.get("event_type") == "sent"]
            opened_events = [e for e in events if e.get("event_type") == "opened"]
            clicked_events = [e for e in events if e.get("event_type") == "clicked"]
            replied_events = [e for e in events if e.get("event_type") == "replied"]
            
            total_sent = len(sent_events)
            total_opened = len(opened_events)
            total_clicked = len(clicked_events)
            total_replied = len(replied_events)
            
            open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
            click_rate = (total_clicked / total_sent * 100) if total_sent > 0 else 0
            reply_rate = (total_replied / total_sent * 100) if total_sent > 0 else 0
            
            return {
                "status": "success",
                "data": {
                    "metrics": {
                        "totalSent": total_sent,
                        "totalOpened": total_opened,
                        "totalClicked": total_clicked,
                        "totalReplied": total_replied,
                        "openRate": round(open_rate, 2),
                        "clickRate": round(click_rate, 2),
                        "replyRate": round(reply_rate, 2),
                        "bounceRate": 0.0
                    },
                    "dailyStats": [],
                    "campaigns": [],
                    "recentEvents": [],
                    "timeRange": time_range
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error fetching email metrics: {str(e)}"
            }
    
    async def get_email_status(self, lead_id: str) -> Dict[str, Any]:
        """Get email status for a lead"""
        try:
            response = self.supabase.table("emails").select("*").eq("lead_id", lead_id).order("created_at", desc=True).limit(1).execute()
            
            if response.data:
                email = response.data[0]
                return {
                    "status": "success",
                    "data": {
                        "emailStatus": email.get("status", "unknown"),
                        "sentAt": email.get("sent_at"),
                        "openedAt": email.get("opened_at"),
                        "clickedAt": email.get("clicked_at"),
                        "repliedAt": email.get("replied_at")
                    }
                }
            else:
                return {
                    "status": "success",
                    "data": {
                        "emailStatus": "not_sent"
                    }
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def get_email_history(self, lead_id: str) -> Dict[str, Any]:
        """Get email history for a lead"""
        try:
            response = self.supabase.table("emails").select("*").eq("lead_id", lead_id).order("created_at", desc=True).execute()
            
            return {
                "status": "success",
                "data": response.data or [],
                "count": len(response.data or [])
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def get_email_config(self) -> Dict[str, Any]:
        """Get email configuration"""
        try:
            return {
                "status": "success",
                "data": {
                    "fromEmail": self.settings.FROM_EMAIL,
                    "resendConfigured": bool(self.settings.RESEND_API_KEY),
                    "openaiConfigured": bool(self.settings.OPENAI_API_KEY),
                    "maxEmailsPerDay": 100,
                    "emailTemplatesEnabled": True,
                    "webhooksEnabled": True
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle email webhook events"""
        try:
            event_type = webhook_data.get("type")
            email_id = webhook_data.get("data", {}).get("email_id")
            
            if not email_id:
                return {
                    "status": "error",
                    "message": "Email ID not found in webhook data"
                }
            
            # Update email record based on event type
            update_data = {}
            
            if event_type == "email.opened":
                update_data["opened_at"] = datetime.now().isoformat()
                update_data["status"] = "opened"
            elif event_type == "email.clicked":
                update_data["clicked_at"] = datetime.now().isoformat()
                update_data["status"] = "clicked"
            elif event_type == "email.replied":
                update_data["replied_at"] = datetime.now().isoformat()
                update_data["status"] = "replied"
            elif event_type == "email.bounced":
                update_data["bounced_at"] = datetime.now().isoformat()
                update_data["status"] = "bounced"
            
            if update_data:
                # Update email record
                self.supabase.table("emails").update(update_data).eq("resend_id", email_id).execute()
                
                # Update lead email status if applicable
                email_result = self.supabase.table("emails").select("lead_id").eq("resend_id", email_id).execute()
                
                if email_result.data and email_result.data[0].get("lead_id"):
                    lead_id = email_result.data[0]["lead_id"]
                    self.supabase.table("leads").update({
                        "email_status": update_data["status"]
                    }).eq("id", lead_id).execute()
            
            return {
                "status": "success",
                "message": "Webhook processed successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing webhook: {str(e)}"
            }
    
    async def update_campaign(self, user_id: str, campaign_id: str, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update email campaign for a user"""
        try:
            campaign_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("email_campaigns").update(campaign_data).eq("id", campaign_id).eq("user_id", user_id).execute()
            
            return {
                "status": "success",
                "message": "Campaign updated successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error updating campaign: {str(e)}"
            }
    
    async def get_campaign_status(self, user_id: str, campaign_id: str) -> Dict[str, Any]:
        """Get campaign status for a user"""
        try:
            result = self.supabase.table("email_campaigns").select("*").eq("id", campaign_id).eq("user_id", user_id).execute()
            
            if not result.data:
                return {
                    "status": "error",
                    "message": "Campaign not found"
                }
            
            return {
                "status": "success",
                "data": result.data[0]
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error getting campaign status: {str(e)}"
            }
    
    async def refresh_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """Refresh dashboard data for a user"""
        try:
            # Get updated email metrics
            metrics = await self.get_email_metrics(user_id, "30d")
            
            # Get updated campaigns
            campaigns = await self.get_email_campaigns(user_id)
            
            return {
                "status": "success",
                "message": "Dashboard data refreshed successfully",
                "data": {
                    "metrics": metrics.get("data", {}),
                    "campaigns": campaigns.get("data", [])
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error refreshing dashboard data: {str(e)}"
            }