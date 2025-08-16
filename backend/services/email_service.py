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
    
    def __init__(self):
        self.settings = get_settings()
        self.supabase = create_client(
            self.settings.SUPABASE_URL,
            self.settings.SUPABASE_SERVICE_ROLE_KEY
        )
        
        # Initialize OpenAI for email generation
        if self.settings.OPENAI_API_KEY:
            self.openai_client = OpenAI(
                api_key=self.settings.OPENAI_API_KEY
            )
        
        # Initialize Resend for email sending
        if self.settings.RESEND_API_KEY:
            resend.api_key = self.settings.RESEND_API_KEY
    
    async def generate_email(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personalized email using AI"""
        try:
            lead_name = params.get("leadName", "")
            lead_company = params.get("leadCompany", "")
            lead_title = params.get("leadTitle", "")
            email_type = params.get("emailType", "cold_outreach")
            tone = params.get("tone", "professional")
            custom_context = params.get("customContext", "")
            
            if not lead_name:
                return {
                    "status": "error",
                    "message": "Lead name is required"
                }
            
            # Generate email using OpenAI
            prompt = self._create_email_prompt(lead_name, lead_company, lead_title, email_type, tone, custom_context)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-5-nano-2025-08-07",
                messages=[
                    {"role": "system", "content": "You are an expert email copywriter."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            email_content = response.choices[0].message.content
            
            return {
                "status": "success",
                "data": {
                    "subject": f"Quick question about {lead_company}",
                    "body": email_content
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def create_draft(self, draft_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create email draft"""
        try:
            draft = {
                "id": str(uuid.uuid4()),
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
    
    async def create_campaign(self, name: str, description: str = None, template_id: str = None, 
                             selected_leads: List[str] = None, email_interval: int = 24, 
                             daily_limit: int = 50, send_time_start: str = "07:00", 
                             send_time_end: str = "09:00", timezone: str = "America/New_York", 
                             scheduled_at: datetime = None) -> Dict[str, Any]:
        """Create email campaign with scheduling parameters"""
        try:
            campaign = {
                "id": str(uuid.uuid4()),
                "name": name,
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
            
            response = self.supabase.table("email_campaigns").insert(campaign).execute()
            
            return {
                "status": "success",
                "data": response.data[0]
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def start_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Start email campaign"""
        try:
            # Update campaign status
            self.supabase.table("email_campaigns").update({
                "status": "active",
                "started_at": datetime.now().isoformat()
            }).eq("id", campaign_id).execute()
            
            return {
                "status": "success",
                "message": "Campaign started successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def pause_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Pause email campaign"""
        try:
            # Update campaign status
            self.supabase.table("email_campaigns").update({
                "status": "paused",
                "paused_at": datetime.now().isoformat()
            }).eq("id", campaign_id).execute()
            
            return {
                "status": "success",
                "message": "Campaign paused successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def resume_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Resume paused email campaign"""
        try:
            # Update campaign status
            self.supabase.table("email_campaigns").update({
                "status": "active",
                "resumed_at": datetime.now().isoformat()
            }).eq("id", campaign_id).execute()
            
            return {
                "status": "success",
                "message": "Campaign resumed successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def delete_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Delete email campaign"""
        try:
            # Delete campaign
            self.supabase.table("email_campaigns").delete().eq("id", campaign_id).execute()
            
            return {
                "status": "success",
                "message": "Campaign deleted successfully"
            }
        except Exception as e:
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
            
            # Create email generation prompt
            prompt = self._create_email_prompt(
                lead_name, lead_company, lead_title, email_type, tone, custom_context
            )
            
            # Generate email using OpenAI
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
                "message": f"Email generation failed: {str(e)}"
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
        """Send email using Resend"""
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
            
            # Send email via Resend
            email_data = {
                "from": from_email,
                "to": [to_email],
                "subject": subject,
                "html": self._format_email_html(body),
                "text": body
            }
            
            response = resend.Emails.send(email_data)
            
            # Save email to database
            email_record = {
                "id": str(uuid.uuid4()),
                "lead_id": lead_id,
                "to_email": to_email,
                "from_email": from_email,
                "subject": subject,
                "body": body,
                "status": "sent",
                "sent_at": datetime.now().isoformat(),
                "resend_id": response.get("id"),
                "created_at": datetime.now().isoformat()
            }
            
            self.supabase.table("emails").insert(email_record).execute()
            
            # Update lead email status
            if lead_id:
                self.supabase.table("leads").update({
                    "email_status": "sent",
                    "last_contacted": datetime.now().isoformat()
                }).eq("id", lead_id).execute()
            
            return {
                "status": "success",
                "message": "Email sent successfully",
                "data": {
                    "emailId": email_record["id"],
                    "resendId": response.get("id")
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Email sending failed: {str(e)}"
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
    
    async def get_email_templates(self) -> Dict[str, Any]:
        """Get all email templates"""
        try:
            response = self.supabase.table("email_templates").select("*").execute()
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
    
    async def save_template(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Save email template"""
        try:
            template_data = {
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
    
    async def update_email_template(self, template_id: str, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update email template"""
        try:
            template_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("email_templates").update(template_data).eq("id", template_id).execute()
            
            return {
                "status": "success",
                "message": "Template updated successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error updating template: {str(e)}"
            }
    
    async def delete_email_template(self, template_id: str) -> Dict[str, Any]:
        """Delete email template"""
        try:
            result = self.supabase.table("email_templates").delete().eq("id", template_id).execute()
            
            return {
                "status": "success",
                "message": "Template deleted successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error deleting template: {str(e)}"
            }
    
    async def delete_template(self, template_id: str) -> Dict[str, Any]:
        """Delete email template (alias method)"""
        return await self.delete_email_template(template_id)
    
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
    
    async def update_email_draft(self, draft_id: str, draft_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update email draft"""
        try:
            draft_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("email_drafts").update(draft_data).eq("id", draft_id).execute()
            
            return {
                "status": "success",
                "message": "Draft updated successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error updating draft: {str(e)}"
            }
    
    async def delete_email_draft(self, draft_id: str) -> Dict[str, Any]:
        """Delete email draft"""
        try:
            result = self.supabase.table("email_drafts").delete().eq("id", draft_id).execute()
            
            return {
                "status": "success",
                "message": "Draft deleted successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error deleting draft: {str(e)}"
            }
    
    async def create_email_campaign(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create email campaign"""
        try:
            campaign = {
                "id": str(uuid.uuid4()),
                "name": campaign_data.get("name"),
                "subject": campaign_data.get("subject"),
                "body": campaign_data.get("body"),
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
    
    async def get_email_campaigns(self) -> Dict[str, Any]:
        """Get email campaigns"""
        try:
            result = self.supabase.table("email_campaigns").select("*").order("created_at", desc=True).execute()
            
            return {
                "status": "success",
                "data": result.data or []
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
    
    async def get_email_metrics(self, time_range: str = "30d") -> Dict[str, Any]:
        """Get email metrics"""
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
            
            # Fetch email events in date range
            events_result = self.supabase.table("email_events").select("*").gte("created_at", start_date.isoformat()).execute()
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