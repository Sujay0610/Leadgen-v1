from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum

# Chat models
class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[datetime] = None

class ChatRequest(BaseModel):
    message: str
    conversationHistory: Optional[List[ChatMessage]] = None

class ChatResponse(BaseModel):
    status: str
    action: str
    message: str
    leads: Optional[List[Dict[str, Any]]] = None
    count: Optional[int] = None

# Lead generation models
class LeadGenerationMethod(str, Enum):
    apollo = "apollo"
    google_apify = "google_apify"

class LeadGenerationRequest(BaseModel):
    method: LeadGenerationMethod
    jobTitles: List[str]
    locations: List[str]
    industries: Optional[List[str]] = None
    companySizes: Optional[List[str]] = None
    limit: int = 10

class LeadGenerationResponse(BaseModel):
    status: str
    message: str
    leads: Optional[List[Dict[str, Any]]] = None
    count: Optional[int] = None

# Lead CRUD models
class LeadActionRequest(BaseModel):
    action: str  # "update", "delete", "bulk_delete"
    leadId: Optional[str] = None
    leadIds: Optional[List[str]] = None
    leadData: Optional[Dict[str, Any]] = None

class LeadUpdateRequest(BaseModel):
    id: str
    fullName: Optional[str] = None
    email: Optional[str] = None
    jobTitle: Optional[str] = None
    companyName: Optional[str] = None
    companyIndustry: Optional[str] = None
    location: Optional[str] = None
    icpScore: Optional[float] = None
    emailStatus: Optional[str] = None
    notes: Optional[str] = None

class Lead(BaseModel):
    id: str
    fullName: str
    email: Optional[str] = None
    jobTitle: Optional[str] = None
    companyName: Optional[str] = None
    companyIndustry: Optional[str] = None
    location: Optional[str] = None
    icpScore: Optional[float] = None
    icpGrade: Optional[str] = None
    emailStatus: Optional[str] = None
    source: Optional[str] = None
    createdAt: datetime
    updatedAt: Optional[datetime] = None

# Email models
class EmailSendRequest(BaseModel):
    leadId: str
    subject: str
    body: str
    templateId: Optional[str] = None
    campaignId: Optional[str] = None
    scheduledAt: Optional[datetime] = None

class EmailTemplateRequest(BaseModel):
    action: str  # "generate", "create", "use"
    templateId: Optional[str] = None
    leadId: Optional[str] = None
    name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    persona: Optional[str] = None
    stage: Optional[str] = None
    leadData: Optional[Dict[str, Any]] = None

class EmailDraftRequest(BaseModel):
    action: str  # "create", "send"
    draftId: Optional[str] = None
    leadId: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    persona: Optional[str] = None
    stage: Optional[str] = None
    templateId: Optional[str] = None
    campaignId: Optional[str] = None
    scheduledAt: Optional[datetime] = None

class EmailDraftUpdateRequest(BaseModel):
    id: str
    subject: Optional[str] = None
    body: Optional[str] = None
    scheduledAt: Optional[datetime] = None
    campaignId: Optional[str] = None

class EmailCampaignRequest(BaseModel):
    action: str  # "create", "start", "pause"
    campaignId: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    templateId: Optional[str] = None
    selectedLeads: Optional[List[str]] = None
    emailInterval: Optional[int] = 24  # hours between emails
    dailyLimit: Optional[int] = 50
    sendTimeStart: Optional[str] = "07:00"
    sendTimeEnd: Optional[str] = "09:00"
    timezone: Optional[str] = "America/New_York"
    scheduledAt: Optional[datetime] = None

class EmailCampaignUpdateRequest(BaseModel):
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    templateId: Optional[str] = None
    selectedLeads: Optional[List[str]] = None
    emailInterval: Optional[int] = None
    dailyLimit: Optional[int] = None
    sendTimeStart: Optional[str] = None
    sendTimeEnd: Optional[str] = None
    timezone: Optional[str] = None
    scheduledAt: Optional[datetime] = None

class EmailDashboardRequest(BaseModel):
    action: str  # "refresh", "export"
    timeRange: Optional[str] = "30"
    format: Optional[str] = "json"

# ICP models
class ICPScoringCriteria(BaseModel):
    industryFit: Dict[str, float]
    roleFit: Dict[str, float]
    companySizeFit: Dict[str, float]
    decisionMaker: Dict[str, float]

class ICPTargetingRules(BaseModel):
    operations: Dict[str, Any]
    fieldService: Dict[str, Any]

class ICPConfigRequest(BaseModel):
    scoringCriteria: Optional[ICPScoringCriteria] = None
    targetingRules: Optional[ICPTargetingRules] = None
    customPrompt: Optional[str] = None

# Webhook models
class WebhookEvent(BaseModel):
    type: str
    data: Dict[str, Any]
    created_at: Optional[str] = None

# Response models
class APIResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

class PaginatedResponse(BaseModel):
    status: str
    data: List[Dict[str, Any]]
    pagination: Dict[str, Any]
    total: int

# Metrics models
class LeadMetrics(BaseModel):
    totalLeads: int
    newLeads: int
    averageScore: float
    topGrade: str
    emailsSent: int
    emailsOpened: int
    emailsClicked: int
    emailsReplied: int

class EmailMetrics(BaseModel):
    totalSent: int
    totalOpened: int
    totalClicked: int
    totalReplied: int
    openRate: float
    clickRate: float
    replyRate: float
    bounceRate: float

class DailyStats(BaseModel):
    date: str
    sent: int
    opened: int
    clicked: int
    replied: int

class CampaignPerformance(BaseModel):
    id: str
    name: str
    sent: int
    opened: int
    clicked: int
    replied: int
    openRate: float
    clickRate: float
    replyRate: float

class EmailEvent(BaseModel):
    id: str
    type: str
    leadName: str
    companyName: str
    subject: str
    timestamp: str

class CampaignStatusRequest(BaseModel):
    action: str  # "start", "pause", "resume"

# Batch enrichment models
class BatchEnrichmentRequest(BaseModel):
    profileUrls: List[str] = Field(..., description="List of LinkedIn profile URLs to enrich")

class BatchEnrichmentResponse(BaseModel):
    status: str
    message: str
    enriched_profiles: List[Dict[str, Any]]
    count: int