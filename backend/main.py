from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
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
from dependencies.auth import get_current_user, get_optional_user, get_user_from_token_param
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

# Add authentication to existing endpoints - DEPRECATED
# Use /api/leads instead

# Chat endpoints
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest, background_tasks: BackgroundTasks, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        # Convert ChatMessage objects to dict format expected by ChatService
        conversation_history = []
        if request.conversationHistory:
            for msg in request.conversationHistory:
                conversation_history.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Extract method from context
        method = request.context.get("method", "apollo") if request.context else "apollo"
        
        # Call the correct method with proper parameters
        response = await chat_service.process_chat_message({
            "message": request.message,
            "conversationHistory": conversation_history,
            "context": {
                "leadGenerationMode": True,
                "method": method
            }
        })
        
        if response["status"] == "success":
            # Check if the response contains structured data for lead generation
            structured_data = response["data"].get("structuredData")
            if structured_data and any(key in structured_data for key in ['jobTitles', 'locations', 'industries']):
                # Try to generate leads using the structured data
                try:
                    # Generate session ID for status tracking
                    session_id = str(uuid.uuid4())
                    
                    lead_params = {
                        "method": method,  # Use the method from context
                        "jobTitles": structured_data.get("jobTitles", []),
                        "locations": structured_data.get("locations", []),
                        "industries": structured_data.get("industries", []),
                        "companySizes": structured_data.get("companySizes", []),
                        "limit": 10
                    }
                    
                    # Generate leads in background with session tracking
                    async def run_lead_generation():
                        try:
                            result = await lead_service.generate_leads(lead_params, session_id)
                            print(f"Lead generation completed for session {session_id}: {result}")
                        except Exception as e:
                            print(f"Error in background lead generation: {e}")
                            lead_service.emit_status(session_id, {
                                "type": "error",
                                "message": str(e),
                                "timestamp": datetime.now().isoformat()
                            })
                    
                    # Start background task
                    background_tasks.add_task(run_lead_generation)
                    
                    return {
                        "status": "success",
                        "data": {
                            "response": f"{response['data']['response']} Perfect! I'm now generating leads for you. You can track the progress using the session ID.",
                            "conversationId": response["data"].get("conversationId"),
                            "sessionId": session_id,
                            "leadGeneration": {
                                "status": "started",
                                "method": method,
                                "parameters": lead_params
                            },
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
async def chat_get_endpoint(action: str = None, current_user: Dict[str, Any] = Depends(get_current_user)):
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
async def generate_leads_endpoint(request: LeadGenerationRequest, background_tasks: BackgroundTasks, current_user: Dict[str, Any] = Depends(get_current_user), session_id: Optional[str] = Query(None)):
    """Original lead generation endpoint with authentication"""
    print(f"Lead generation started with session_id: {session_id}")
    try:
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Convert request to dict format expected by lead_service
        params = {
            "method": request.method,
            "jobTitles": request.jobTitles,
            "locations": request.locations,
            "industries": request.industries,
            "companySizes": request.companySizes,
            "limit": request.limit,
            "user_id": current_user["user_id"]
        }
        
        # Start lead generation in background using the correct method
        async def run_lead_generation():
            try:
                result = await lead_service.generate_leads(params, session_id)
                print(f"Lead generation completed for session {session_id}: {result}")
            except Exception as e:
                print(f"Error in background lead generation: {e}")
                lead_service.emit_status(session_id, {
                    "status": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        background_tasks.add_task(run_lead_generation)
        
        return {
            "status": "success",
            "message": "Lead generation started",
            "session_id": session_id,
            "user_id": current_user["user_id"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error in lead generation: {e}")
        return {
            "status": "error",
            "message": str(e),
            "session_id": session_id if 'session_id' in locals() else "unknown",
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/generate-leads-test")
async def generate_leads_test_endpoint(request: LeadGenerationRequest, background_tasks: BackgroundTasks, session_id: Optional[str] = Query(None)):
    """Test lead generation endpoint without authentication for testing purposes"""
    print(f"Test lead generation started with session_id: {session_id}")
    try:
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Create a test user context
        test_user = {
            "user_id": "test-user-123",
            "email": "test@example.com"
        }
        
        # Convert request to dict format expected by lead_service
        params = {
            "method": request.method,
            "jobTitles": request.jobTitles,
            "locations": request.locations,
            "industries": request.industries,
            "companySizes": request.companySizes,
            "limit": request.limit,
            "user_id": test_user["user_id"]
        }
        
        # Start lead generation in background using the correct method
        async def run_lead_generation():
            try:
                result = await lead_service.generate_leads(params, session_id)
                print(f"Lead generation completed for session {session_id}: {result}")
            except Exception as e:
                print(f"Error in background lead generation: {e}")
                lead_service.emit_status(session_id, {
                    "status": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        background_tasks.add_task(run_lead_generation)
        
        return {
            "status": "success",
            "message": "Test lead generation started",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error in test lead generation: {e}")
        return {
            "status": "error",
            "message": str(e),
            "session_id": session_id if 'session_id' in locals() else "unknown",
            "timestamp": datetime.now().isoformat()
        }

    return {
        "status": "success",
        "message": "Test lead generation started",
        "session_id": session_id,
        "user_id": test_user["user_id"],
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/generate-leads-original")
async def generate_leads_endpoint_original(request: LeadGenerationRequest, current_user: Dict[str, Any] = Depends(get_current_user), session_id: Optional[str] = Query(None)):
    print(f"Lead generation started with session_id: {session_id}")
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
            "limit": request.limit,
            "user_id": current_user["user_id"]
        }, session_id)
        
        # Don't close the status session here - let the SSE endpoint handle cleanup
        # lead_service.close_status_session(session_id)
        
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
async def generate_leads_status(session_id: str, include_history: bool = False, current_user: Dict[str, Any] = Depends(get_user_from_token_param)):
    """REST endpoint for polling lead generation status"""
    try:
        # Get current status from lead service
        status = lead_service.get_status(session_id, include_history=include_history)
        print(f"[STATUS] Retrieved status for session {session_id} (include_history={include_history}): {status.get('type', 'unknown')}")
        
        return JSONResponse(content={
            "success": True,
            "data": status
        })
        
    except Exception as e:
        print(f"[STATUS] Error getting status for session {session_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.get("/api/generate-leads/status-test")
async def generate_leads_status_test(session_id: str, include_history: bool = False):
    """Test REST endpoint for polling status without authentication"""
    try:
        # Get current status from lead service
        status = lead_service.get_status(session_id, include_history=include_history)
        print(f"[STATUS TEST] Retrieved status for session {session_id} (include_history={include_history}): {status.get('type', 'unknown')}")
        
        return JSONResponse(content={
            "success": True,
            "data": status
        })
        
    except Exception as e:
        print(f"[STATUS TEST] Error getting status for session {session_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

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
    sortOrder: str = "desc",
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        result = await lead_service.get_leads(
            user_id=current_user["user_id"],
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
async def leads_post_endpoint(request: LeadActionRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        if request.action == "update":
            result = await lead_service.update_lead(current_user["user_id"], request.leadId, request.leadData)
        elif request.action == "delete":
            result = await lead_service.delete_lead(current_user["user_id"], request.leadId)
        elif request.action == "bulk_delete":
            result = await lead_service.bulk_delete_leads(current_user["user_id"], request.leadIds)
        else:
            raise HTTPException(status_code=400, detail="Invalid action specified")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/leads")
async def update_lead_endpoint(request: LeadUpdateRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        result = await lead_service.update_lead(current_user["user_id"], request.id, request.dict(exclude={"id"}))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/leads")
async def delete_lead_endpoint(id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        result = await lead_service.delete_lead(current_user["user_id"], id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Lead metrics endpoint
@app.get("/api/leads/metrics")
async def get_lead_metrics(timeRange: str = "30d", current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        result = await lead_service.get_metrics(current_user["user_id"], timeRange)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Batch enrichment endpoint
@app.post("/api/leads/enrich-batch")
async def enrich_profiles_batch(request: BatchEnrichmentRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        enriched_profiles = await lead_service.enrich_profile_with_apify(request.profileUrls, current_user["user_id"])
        
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
async def send_email_endpoint(request: EmailSendRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        result = await email_service.send_email(request, current_user["user_id"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/email/send")
async def email_send_get_endpoint(action: str = None, leadId: str = None, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        if action == "status" and leadId:
            result = await email_service.get_email_status(current_user["user_id"], leadId)
        elif action == "history" and leadId:
            result = await email_service.get_email_history(current_user["user_id"], leadId)
        elif action == "config":
            result = await email_service.get_email_config()
        else:
            raise HTTPException(status_code=400, detail="Invalid action specified")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/email/generate")
async def generate_email_endpoint(request: EmailGenerationRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        result = await email_service.generate_email({
            "leadName": request.leadName,
            "leadCompany": request.leadCompany,
            "leadTitle": request.leadTitle,
            "emailType": request.emailType,
            "tone": request.tone,
            "customContext": request.customContext,
            "templateId": getattr(request, 'templateId', None),
            "leadData": getattr(request, 'leadData', None)
        })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Email templates endpoints
@app.get("/api/email/templates")
async def get_email_templates(
    persona: str = None,
    stage: str = None,
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        result = await email_service.get_email_templates(current_user["user_id"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/email/templates")
async def email_templates_post_endpoint(request: EmailTemplateRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        if request.action == "create":
            result = await email_service.save_template(current_user["user_id"], {
                "name": request.name,
                "subject": request.subject,
                "body": request.body,
                "persona": request.persona,
                "stage": request.stage
            })
        elif request.action == "generate":
            result = await email_service.generate_template(
                current_user["user_id"], request.persona, request.stage, request.leadData
            )
        elif request.action == "save":
            result = await email_service.save_template(request, current_user["user_id"])
        elif request.action == "use":
            result = await email_service.use_template(current_user["user_id"], request.templateId)
        else:
            raise HTTPException(status_code=400, detail="Invalid action specified")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/email/templates/{template_id}")
async def update_email_template(template_id: str, request: EmailTemplateRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        template_data = {
            "subject": request.subject,
            "body": request.body,
            "persona": request.persona,
            "stage": request.stage
        }
        result = await email_service.update_email_template(current_user["user_id"], template_id, template_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/email/templates/{template_id}")
async def delete_email_template(template_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        result = await email_service.delete_template(current_user["user_id"], template_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Email drafts endpoints
@app.get("/api/email/drafts")
async def get_email_drafts(
    leadId: str = None,
    status: str = None,
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        result = await email_service.get_email_drafts(current_user["user_id"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/email/drafts")
async def email_drafts_post_endpoint(request: EmailDraftRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        if request.action == "create":
            result = await email_service.create_draft({
            "leadId": request.leadId,
            "subject": request.subject,
            "body": request.body,
            "persona": request.persona,
            "stage": request.stage,
            "user_id": current_user["user_id"]
        })
        elif request.action == "send":
            result = await email_service.send_draft(current_user["user_id"], request.draftId)
        else:
            raise HTTPException(status_code=400, detail="Invalid action specified")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/email/drafts")
async def update_email_draft(request: EmailDraftUpdateRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        result = await email_service.update_email_draft(current_user["user_id"], request.id, request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Email campaigns endpoints
@app.get("/api/email/campaigns")
async def get_email_campaigns(
    status: str = None,
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        result = await email_service.get_email_campaigns(current_user["user_id"])
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
            user_id=current_user["user_id"],
            name=request.name,
            description=request.description,
            template_id=request.templateId,
            selected_leads=request.selectedLeads,
            email_interval=request.emailInterval,
            daily_limit=request.dailyLimit,
            send_time_start=request.sendTimeStart,
            send_time_end=request.sendTimeEnd,
            timezone=request.timezone,
            scheduled_at=request.scheduledAt
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/email/campaigns")
async def update_email_campaign(request: EmailCampaignUpdateRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        result = await email_service.update_campaign(current_user["user_id"], request.id, request)
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
            result = await email_service.start_campaign(current_user["user_id"], campaign_id)
        elif request.action == "pause":
            result = await email_service.pause_campaign(current_user["user_id"], campaign_id)
        elif request.action == "resume":
            result = await email_service.resume_campaign(current_user["user_id"], campaign_id)
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/email/campaigns/{campaign_id}/status")
async def get_campaign_status(campaign_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        result = await email_service.get_campaign_status(current_user["user_id"], campaign_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/email/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Delete email campaign"""
    try:
        result = await email_service.delete_campaign(current_user["user_id"], campaign_id)
        if result["status"] == "error" and "not found" in result["message"].lower():
            raise HTTPException(status_code=404, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Email dashboard endpoint
@app.get("/api/email/dashboard")
async def get_email_dashboard(timeRange: str = "30", current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        result = await email_service.get_email_metrics(current_user["user_id"], f"{timeRange}d")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/email/dashboard")
async def email_dashboard_post_endpoint(request: EmailDashboardRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        if request.action == "refresh":
            result = await email_service.refresh_dashboard_data(current_user["user_id"])
            return result
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
async def get_icp_config(current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        result = await icp_service.get_config(current_user["user_id"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/icp/config")
async def update_icp_config(request: ICPConfigRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        result = await icp_service.update_config(current_user["user_id"], request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ICP prompt configuration endpoints
@app.post("/api/icp/prompt")
async def update_icp_prompt(request: dict, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        # Update both prompt and default values together in a single operation
        prompt = request.get("prompt", "")
        default_values = request.get("default_values", {})
        
        # Use the combined update method
        result = lead_service.ai_icp_scorer.update_prompt_and_values(prompt, default_values)
        
        return {
            "status": "success",
            "message": "ICP prompt updated successfully"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
            }

@app.get("/api/icp/prompt")
async def get_icp_prompt(current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        # Unwrap the scorer response to return a clean shape
        prompt_result = lead_service.ai_icp_scorer.get_prompt()
        data = prompt_result.get("data", {}) if isinstance(prompt_result, dict) else {}
        prompt_raw = data.get("prompt", "")
        
        # Handle nested prompt data - extract string from nested objects
        prompt_str = prompt_raw
        if isinstance(prompt_raw, dict):
            # If prompt is a dict, try to extract the actual prompt string
            if "data" in prompt_raw and isinstance(prompt_raw["data"], dict):
                prompt_str = prompt_raw["data"].get("prompt", "")
            elif "prompt" in prompt_raw:
                prompt_str = prompt_raw["prompt"]
            else:
                # If we can't extract a string, use the default
                prompt_str = lead_service.ai_icp_scorer._get_default_prompt()
        elif isinstance(prompt_raw, str):
            try:
                # Try to parse as JSON in case it's a JSON string
                parsed = json.loads(prompt_raw)
                if isinstance(parsed, dict):
                    if "data" in parsed and isinstance(parsed["data"], dict):
                        prompt_str = parsed["data"].get("prompt", prompt_raw)
                    elif "prompt" in parsed:
                        prompt_str = parsed["prompt"]
                    else:
                        prompt_str = prompt_raw
                else:
                    prompt_str = prompt_raw
            except (json.JSONDecodeError, TypeError):
                # If it's not valid JSON, use as-is
                prompt_str = prompt_raw
        
        # Ensure we have a string
        if not isinstance(prompt_str, str) or not prompt_str.strip():
            prompt_str = lead_service.ai_icp_scorer._get_default_prompt()
            
        # Get default values from the get_prompt method if not found in data
        if "default_values" not in data or not data["default_values"]:
            default_prompt_result = lead_service.ai_icp_scorer.get_prompt()
            default_data = default_prompt_result.get("data", {}) if isinstance(default_prompt_result, dict) else {}
            default_vals = default_data.get("default_values", {
                "target_roles": "Operations Manager, Facility Manager, Maintenance Manager",
                "target_industries": "Manufacturing, Industrial, Automotive",
                "target_company_sizes": "51-200, 201-500, 501-1000",
                "target_locations": "United States",
                "target_seniority": "Manager, Director, VP, C-Level"
            })
        else:
            default_vals = data.get("default_values")
        return {
            "prompt": prompt_str,
            "default_values": default_vals
        }
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

# Add test mode configuration
TEST_MODE = False  # Global test mode flag

# Update email service initialization
email_service = EmailService(test_mode=TEST_MODE)

# Add endpoint to toggle test mode
@app.post("/api/email/test-mode")
async def toggle_test_mode(request: dict, current_user: Dict[str, Any] = Depends(get_current_user)):
    global TEST_MODE, email_service
    try:
        TEST_MODE = request.get("enabled", False)
        # Reinitialize email service with new test mode
        email_service = EmailService(test_mode=TEST_MODE)
        
        return {
            "status": "success",
            "message": f"Test mode {'enabled' if TEST_MODE else 'disabled'}",
            "testMode": TEST_MODE
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/email/test-mode")
async def get_test_mode(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "status": "success",
        "testMode": TEST_MODE
    }

@app.post("/api/email/process-scheduled")
async def process_scheduled_emails_endpoint(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Process scheduled emails that are due to be sent"""
    try:
        result = await email_service.process_scheduled_emails()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing scheduled emails: {str(e)}")

# Background task to process scheduled emails every minute
import threading
import time

def background_email_processor():
    """Background task to process scheduled emails"""
    import asyncio
    
    print("[EMAIL PROCESSOR] Background email processor started")
    
    async def process_emails():
        try:
            print("[EMAIL PROCESSOR] Checking for scheduled emails...")
            result = await email_service.process_scheduled_emails()
            print(f"[EMAIL PROCESSOR] Processed scheduled emails: {result}")
        except Exception as e:
            print(f"[EMAIL PROCESSOR] Background email processing error: {e}")
    
    while True:
        try:
            # Run the async function in the background
            asyncio.run(process_emails())
        except Exception as e:
            print(f"[EMAIL PROCESSOR] Background task error: {e}")
        
        # Wait 60 seconds before next check
        time.sleep(60)

# Start background task
background_thread = threading.Thread(target=background_email_processor, daemon=True)
background_thread.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)