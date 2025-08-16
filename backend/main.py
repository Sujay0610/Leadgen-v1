from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from sse_starlette.sse import EventSourceResponse
import os
import uuid
from datetime import datetime, timedelta
import json
import asyncio
from supabase import create_client, Client
import openai
from openai import OpenAI
import requests
import hashlib
from collections import deque
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import resend

# Import custom modules
from models import *
from models import BatchEnrichmentRequest, BatchEnrichmentResponse, CampaignStatusRequest
from services.lead_service import LeadService
from services.email_service import EmailService
from services.chat_service import ChatService
from services.icp_service import ICPService
from services.auth_service import AuthService
from config import get_settings
from dependencies.auth import get_current_user, get_optional_user
from routes import auth

app = FastAPI(
    title="Lead Generation API",
    description="FastAPI backend for lead generation and email automation with authentication",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get settings
settings = get_settings()

# Include auth router
app.include_router(auth.router)

# Initialize services
lead_service = LeadService()
email_service = EmailService()
chat_service = ChatService()
icp_service = ICPService()
auth_service = AuthService()

# Include routers
app.include_router(auth.router)

@app.get("/")
async def root():
    return {"message": "Lead Generation API is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "supabase": bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY),
            "openai": bool(settings.OPENAI_API_KEY),
            "resend": bool(settings.RESEND_API_KEY),
            "apify": bool(settings.APIFY_API_TOKEN),
            "auth": True
        }
    }

# Protected endpoint example
@app.get("/protected")
async def protected_endpoint(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "message": "This is a protected endpoint",
        "user": current_user
    }

# Add authentication to existing endpoints
@app.get("/leads")
async def get_leads():
    # Your existing leads logic here
    pass

# Chat endpoints
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Convert ChatMessage objects to dict format expected by ChatService
        conversation_history = []
        if request.conversationHistory:
            for msg in request.conversationHistory:
                conversation_history.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Call the correct method with proper parameters
        response = await chat_service.process_chat_message({
            "message": request.message,
            "conversationHistory": conversation_history,
            "context": {"leadGenerationMode": True}
        })
        
        if response["status"] == "success":
            # Check if the response contains structured data for lead generation
            structured_data = response["data"].get("structuredData")
            if structured_data and any(key in structured_data for key in ['jobTitles', 'locations', 'industries']):
                # Try to generate leads using the structured data
                try:
                    lead_params = {
                        "method": "apollo",  # Default method
                        "jobTitles": structured_data.get("jobTitles", []),
                        "locations": structured_data.get("locations", []),
                        "industries": structured_data.get("industries", []),
                        "companySizes": structured_data.get("companySizes", []),
                        "limit": 10
                    }
                    
                    lead_result = await lead_service.generate_leads(lead_params)
                    
                    if lead_result["status"] == "success":
                        return {
                            "status": "success",
                            "data": {
                                "response": f"{response['data']['response']} Found {lead_result['count']} leads!",
                                "leads": lead_result["leads"],
                                "count": lead_result["count"],
                                "conversationId": response["data"].get("conversationId"),
                                "timestamp": response["data"].get("timestamp")
                            }
                        }
                    else:
                        return {
                            "status": "success",
                            "data": {
                                "response": f"I tried to generate leads but encountered an issue: {lead_result['message']}. Please try refining your search criteria.",
                                "conversationId": response["data"].get("conversationId"),
                                "timestamp": response["data"].get("timestamp")
                            }
                        }
                except Exception as error:
                    return {
                        "status": "success",
                        "data": {
                            "response": "I encountered an error while generating leads. Please try again or contact support if the issue persists.",
                            "conversationId": response["data"].get("conversationId"),
                            "timestamp": response["data"].get("timestamp")
                        }
                    }
            
            # For regular chat responses
            return {
                "status": "success",
                "data": {
                    "response": response["data"]["response"],
                    "conversationId": response["data"].get("conversationId"),
                    "structuredData": response["data"].get("structuredData"),
                    "timestamp": response["data"].get("timestamp")
                }
            }
        else:
            return {
                "status": "error",
                "message": response["message"]
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat")
async def chat_get_endpoint(action: str = None):
    try:
        if action == "examples":
            return {
                "status": "success",
                "examples": [
                    "Find operations managers in manufacturing companies in Texas",
                    "I need facility managers at healthcare organizations",
                    "Show me plant managers in the automotive industry",
                    "Find maintenance directors at large companies in California",
                    "I'm looking for decision makers in food processing companies"
                ]
            }
        
        if action == "capabilities":
            return {
                "status": "success",
                "capabilities": {
                    "leadGeneration": True,
                    "apolloIntegration": bool(settings.APOLLO_API_KEY),
                    "googleSearch": bool(settings.GOOGLE_API_KEY),
                    "apifyEnrichment": bool(settings.APIFY_API_TOKEN),
                    "icpScoring": bool(settings.OPENAI_API_KEY),
                    "conversationalAI": bool(settings.OPENAI_API_KEY)
                }
            }
        
        raise HTTPException(status_code=400, detail="Invalid action specified")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Lead generation endpoints
@app.post("/api/generate-leads")
async def generate_leads_endpoint(request: LeadGenerationRequest, session_id: str = None):
    try:
        # Generate a session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
            
        result = await lead_service.generate_leads({
            "method": request.method,
            "jobTitles": request.jobTitles,
            "locations": request.locations,
            "industries": request.industries or [],
            "companySizes": request.companySizes or [],
            "limit": request.limit
        }, session_id)
        
        # Close the status session after completion
        lead_service.close_status_session(session_id)
        
        # Add session_id to response for frontend reference
        if isinstance(result, dict):
            result["session_id"] = session_id
            
        return result
    except Exception as e:
        if session_id:
            lead_service.close_status_session(session_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/generate-leads")
async def generate_leads_config():
    try:
        config = {
            "apollo_configured": bool(settings.APOLLO_API_KEY),
            "google_configured": bool(settings.GOOGLE_API_KEY and settings.GOOGLE_CSE_ID),
            "apify_configured": bool(settings.APIFY_API_TOKEN),
            "openai_configured": bool(settings.OPENAI_API_KEY),
            "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY)
        }
        
        return {
            "status": "success",
            "message": "Lead generation API is running",
            "configuration": config,
            "available_methods": ["apollo", "google_apify"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/generate-leads/status")
async def generate_leads_status(session_id: str):
    """Server-Sent Events endpoint for real-time lead generation status updates"""
    async def event_generator():
        try:
            # Get status updates from lead service
            async for status_update in lead_service.get_status_updates(session_id):
                yield {
                    "event": "status",
                    "data": json.dumps(status_update)
                }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }
    
    return EventSourceResponse(event_generator())

# Leads CRUD endpoints
@app.get("/api/leads")
async def get_leads(
    page: int = 1,
    limit: int = 50,
    search: str = "",
    minScore: float = 0,
    maxScore: float = 100,
    company: str = "",
    jobTitle: str = "",
    emailStatus: str = "",
    sortBy: str = "created_at",
    sortOrder: str = "desc"
):
    try:
        result = await lead_service.get_leads(
            page=page,
            limit=limit,
            search=search,
            min_score=minScore,
            max_score=maxScore,
            company=company,
            job_title=jobTitle,
            email_status=emailStatus,
            sort_by=sortBy,
            sort_order=sortOrder
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/leads")
async def leads_post_endpoint(request: LeadActionRequest):
    try:
        if request.action == "update":
            result = await lead_service.update_lead(request.leadId, request.leadData)
        elif request.action == "delete":
            result = await lead_service.delete_lead(request.leadId)
        elif request.action == "bulk_delete":
            result = await lead_service.bulk_delete_leads(request.leadIds)
        else:
            raise HTTPException(status_code=400, detail="Invalid action specified")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/leads")
async def update_lead_endpoint(request: LeadUpdateRequest):
    try:
        result = await lead_service.update_lead(request.id, request.dict(exclude={"id"}))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/leads")
async def delete_lead_endpoint(id: str):
    try:
        result = await lead_service.delete_lead(id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Lead metrics endpoint
@app.get("/api/leads/metrics")
async def get_lead_metrics(timeRange: str = "30d"):
    try:
        result = await lead_service.get_metrics(timeRange)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Batch enrichment endpoint
@app.post("/api/leads/enrich-batch")
async def enrich_profiles_batch(request: BatchEnrichmentRequest):
    try:
        enriched_profiles = await lead_service.enrich_profile_with_apify(request.profileUrls)
        
        return BatchEnrichmentResponse(
            status="success",
            message=f"Successfully enriched {len(enriched_profiles)} profiles",
            enriched_profiles=enriched_profiles,
            count=len(enriched_profiles)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Email endpoints
@app.post("/api/email/send")
async def send_email_endpoint(request: EmailSendRequest):
    try:
        result = await email_service.send_email(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/email/send")
async def email_send_get_endpoint(action: str = None, leadId: str = None):
    try:
        if action == "status" and leadId:
            result = await email_service.get_email_status(leadId)
        elif action == "history" and leadId:
            result = await email_service.get_email_history(leadId)
        elif action == "config":
            result = await email_service.get_email_config()
        else:
            raise HTTPException(status_code=400, detail="Invalid action specified")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Email templates endpoints
@app.get("/api/email/templates")
async def get_email_templates(
    persona: str = None,
    stage: str = None,
    limit: int = 50
):
    try:
        result = await email_service.get_email_templates()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/email/templates")
async def email_templates_post_endpoint(request: EmailTemplateRequest):
    try:
        if request.action == "create":
            result = await email_service.save_template({
                "name": request.name,
                "subject": request.subject,
                "body": request.body,
                "persona": request.persona,
                "stage": request.stage
            })
        elif request.action == "generate":
            result = await email_service.generate_template(
                request.persona, request.stage, request.leadData
            )
        elif request.action == "save":
            result = await email_service.save_template(request)
        elif request.action == "use":
            result = await email_service.use_template(request.templateId)
        else:
            raise HTTPException(status_code=400, detail="Invalid action specified")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/email/templates/{template_id}")
async def delete_email_template(template_id: str):
    try:
        result = await email_service.delete_template(template_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Email drafts endpoints
@app.get("/api/email/drafts")
async def get_email_drafts(
    leadId: str = None,
    status: str = None,
    limit: int = 50
):
    try:
        result = await email_service.get_email_drafts()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/email/drafts")
async def email_drafts_post_endpoint(request: EmailDraftRequest):
    try:
        if request.action == "create":
            result = await email_service.create_draft({
                "leadId": request.leadId,
                "subject": request.subject,
                "body": request.body,
                "persona": request.persona,
                "stage": request.stage
            })
        elif request.action == "send":
            result = await email_service.send_draft(request.draftId)
        else:
            raise HTTPException(status_code=400, detail="Invalid action specified")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/email/drafts")
async def update_email_draft(request: EmailDraftUpdateRequest):
    try:
        result = await email_service.update_email_draft(request.id, request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Email campaigns endpoints
@app.get("/api/email/campaigns")
async def get_email_campaigns(
    status: str = None,
    limit: int = 50
):
    try:
        result = await email_service.get_email_campaigns()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/email/campaigns")
async def email_campaigns_post_endpoint(
    request: EmailCampaignRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create email campaign"""
    try:
        result = await email_service.create_campaign(
            name=request.name,
            description=request.description,
            template_id=request.template_id,
            selected_leads=request.selected_leads,
            email_interval=request.email_interval,
            daily_limit=request.daily_limit,
            send_time_start=request.send_time_start,
            send_time_end=request.send_time_end,
            timezone=request.timezone,
            scheduled_at=request.scheduled_at
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/email/campaigns")
async def update_email_campaign(request: EmailCampaignUpdateRequest):
    try:
        result = await email_service.update_campaign(request.id, request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/email/campaigns/{campaign_id}/status")
async def update_campaign_status_endpoint(
    campaign_id: str,
    request: CampaignStatusRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update campaign status (start, pause, resume)"""
    try:
        if request.action == "start":
            result = await email_service.start_campaign(campaign_id)
        elif request.action == "pause":
            result = await email_service.pause_campaign(campaign_id)
        elif request.action == "resume":
            result = await email_service.resume_campaign(campaign_id)
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/email/campaigns/{campaign_id}/status")
async def get_campaign_status(campaign_id: str):
    try:
        result = await email_service.get_campaign_status(campaign_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Email dashboard endpoint
@app.get("/api/email/dashboard")
async def get_email_dashboard(timeRange: str = "30"):
    try:
        result = await email_service.get_email_metrics(f"{timeRange}d")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/email/dashboard")
async def email_dashboard_post_endpoint(request: EmailDashboardRequest):
    try:
        if request.action == "refresh":
            return {"status": "success", "message": "Dashboard data refreshed"}
        elif request.action == "export":
            # Export dashboard functionality not implemented yet
            result = {"status": "error", "message": "Export dashboard not implemented"}
            return result
        else:
            raise HTTPException(status_code=400, detail="Invalid action specified")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ICP configuration endpoints
@app.get("/api/icp/config")
async def get_icp_config():
    try:
        result = await icp_service.get_config()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/icp/config")
async def update_icp_config(request: ICPConfigRequest):
    try:
        result = await icp_service.update_config(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Webhook endpoint
@app.post("/api/webhook")
async def webhook_endpoint(request: dict, background_tasks: BackgroundTasks):
    try:
        # Add webhook processing to background tasks
        background_tasks.add_task(email_service.process_webhook, request)
        return {"status": "success", "message": "Webhook received"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/webhook")
async def webhook_get_endpoint(action: str = None):
    try:
        if action == "status":
            return {
                "status": "success",
                "webhook": {
                    "configured": bool(settings.RESEND_WEBHOOK_SECRET),
                    "endpoint": f"{settings.BASE_URL}/api/webhook"
                }
            }
        elif action == "test":
            test_event = {
                "type": "email.opened",
                "data": {
                    "email_id": "test-email-id",
                    "to": ["test@example.com"],
                    "created_at": datetime.now().isoformat()
                }
            }
            return {
                "status": "success",
                "message": "Webhook test completed",
                "testEvent": test_event
            }
        else:
            return {
                "status": "success",
                "message": "Webhook endpoint is active",
                "supportedEvents": [
                    "email.sent",
                    "email.delivered",
                    "email.delivery_delayed",
                    "email.complained",
                    "email.bounced",
                    "email.opened",
                    "email.clicked"
                ]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)