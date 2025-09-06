import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { createClient } from '@supabase/supabase-js';

class ApiClient {
  private client: AxiosInstance;
  private supabase;

  constructor() {
    this.supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );

    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://leadapi.aigentsify.com',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      async (config) => {
        // Add Supabase JWT token to requests
        const { data: { session } } = await this.supabase.auth.getSession();
        if (session?.access_token) {
          config.headers.Authorization = `Bearer ${session.access_token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        return response;
      },
      (error) => {
        // Handle common errors here
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  // Health check
  async healthCheck() {
    return this.client.get('/health');
  }

  // Chat endpoints
  async sendChatMessage(data: {
    message: string;
    conversationHistory?: Array<{ role: string; content: string }>;
    context?: Record<string, any>;
  }) {
    return this.client.post('/api/chat', data);
  }

  async getChatHistory(limit?: number) {
    return this.client.get('/api/chat/history', { params: { limit } });
  }

  async generateLeadSuggestions(data: {
    industry?: string;
    companySize?: string;
    location?: string;
    goals?: string;
  }) {
    return this.client.post('/api/chat/lead-suggestions', data);
  }

  async analyzeLeadQuality(leadData: Record<string, any>) {
    return this.client.post('/api/chat/analyze-lead', { leadData });
  }

  async generateOutreachSequence(data: {
    leadInfo: Record<string, any>;
    sequenceType?: string;
    numTouches?: number;
  }) {
    return this.client.post('/api/chat/outreach-sequence', data);
  }

  // Lead generation endpoints
  async generateLeads(data: {
    method: 'apollo' | 'google_apify';
    jobTitles: string[];
    locations: string[];
    industries?: string[];
    companySizes?: string[];
    limit?: number;
    session_id?: string;
  }) {
    const { session_id, ...requestData } = data;
    const params = session_id ? { session_id } : {};
    // Use longer timeout for lead generation (15 minutes)
    return this.client.post('/api/generate-leads', requestData, { 
      params,
      timeout: 900000 // 15 minutes
    });
  }

  async getLeadGenerationStatus(sessionId: string) {
    return this.client.get('/api/generate-leads/status', {
      params: { session_id: sessionId },
      timeout: 120000 // 2 minutes timeout for status polling
    });
  }

  // Get authentication token for SSE connections
  async getAuthToken(): Promise<string | null> {
    const { data: { session } } = await this.supabase.auth.getSession();
    return session?.access_token || null;
  }

  async getLeads(params: {
    page?: number;
    limit?: number;
    search?: string;
    minScore?: number;
    maxScore?: number;
    company?: string;
    jobTitle?: string;
    emailStatus?: string;
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
  } = {}) {
    const response = await this.client.get('/api/leads', { params });
    return response;
  }

  async getLead(leadId: string) {
    return this.client.get(`/api/leads/${leadId}`);
  }

  async updateLead(leadId: string, data: Record<string, any>) {
    return this.client.put('/api/leads', { id: leadId, ...data });
  }

  async deleteLead(leadId: string) {
    return this.client.delete('/api/leads', { params: { id: leadId } });
  }

  async bulkDeleteLeads(leadIds: string[]) {
    return this.client.post('/api/leads', { action: 'bulk_delete', leadIds });
  }

  async getLeadMetrics(timeRange: string = '30d') {
    return this.client.get('/api/leads/metrics', { params: { timeRange } });
  }

  // Email endpoints
  async generateEmail(data: {
    leadName: string;
    leadCompany?: string;
    leadTitle?: string;
    emailType?: string;
    tone?: string;
    customContext?: string;
    templateId?: string;
    leadData?: Record<string, any>;
    stage?: string;
  }) {
    return this.client.post('/api/email/generate', data);
  }

  async sendEmail(data: {
    to: string;
    subject: string;
    body: string;
    leadId?: string;
    from?: string;
    metadata?: Record<string, any>;
  }) {
    return this.client.post('/api/email/send', data);
  }

  async getEmailTemplates() {
    const response = await this.client.get('/api/email/templates');
    return response.data;
  }

  async createEmailTemplate(data: {
    name: string;
    subject: string;
    body: string;
    persona?: string;
    stage?: string;
    type?: string;
    variables?: string[];
    isActive?: boolean;
  }) {
    const response = await this.client.post('/api/email/templates', {
      action: 'create',
      name: data.name,
      subject: data.subject,
      body: data.body,
      persona: data.persona,
      stage: data.stage
    });
    return response.data;
  }

  async updateEmailTemplate(templateId: string, data: Record<string, any>) {
    const response = await this.client.put(`/api/email/templates/${templateId}`, {
      subject: data.subject,
      body: data.body,
      persona: data.persona,
      stage: data.stage
    });
    return response.data;
  }

  async deleteEmailTemplate(templateId: string) {
    const response = await this.client.delete(`/api/email/templates/${templateId}`);
    return response.data;
  }

  async getEmailDrafts(userId?: string) {
    return this.client.get('/api/email/drafts', { params: { userId } });
  }

  async saveEmailDraft(data: {
    userId?: string;
    leadId?: string;
    to: string;
    subject: string;
    body: string;
  }) {
    return this.client.post('/api/email/drafts', data);
  }

  async updateEmailDraft(draftId: string, data: Record<string, any>) {
    return this.client.put('/api/email/drafts', { id: draftId, ...data });
  }

  async deleteEmailDraft(draftId: string) {
    return this.client.delete('/api/email/drafts', { params: { id: draftId } });
  }

  async createEmailCampaign(data: {
    name: string;
    templateId: string;
    selectedLeads: string[];
    emailInterval: number;
    dailyLimit: number;
    sendTimeStart: string;
    sendTimeEnd: string;
    timezone: string;
  }) {
    const response = await this.client.post('/api/email/campaigns', data);
    return response.data;
  }

  async getEmailCampaigns() {
    const response = await this.client.get('/api/email/campaigns');
    return response.data;
  }

  async updateCampaignStatus(campaignId: string, action: 'start' | 'pause' | 'resume') {
    const response = await this.client.patch(`/api/email/campaigns/${campaignId}/status`, { action });
    return response.data;
  }

  async updateCampaign(campaignId: string, data: Record<string, any>) {
    const response = await this.client.put('/api/email/campaigns', { id: campaignId, ...data });
    return response.data;
  }

  async deleteCampaign(campaignId: string) {
    const response = await this.client.delete(`/api/email/campaigns/${campaignId}`);
    return response.data;
  }

  async getEmailMetrics(timeRange: string = '30d') {
    return this.client.get('/api/email/dashboard', { params: { timeRange } });
  }

  async getEmailDashboard(timeRange: string = '30d') {
    return this.client.get('/api/email/dashboard', { params: { timeRange } });
  }

  // ICP endpoints
  async getICPSettings() {
    const response = await this.client.get('/api/icp/config');
    return {
      status: response.data.status,
      data: response.data.data
    };
  }

  async updateICPSettings(data: Record<string, any>) {
    return this.client.post('/api/icp/config', data);
  }

  async getICPStats() {
    const response = await this.client.get('/api/icp/config');
    return {
      status: response.data.status,
      data: response.data.statistics
    };
  }

  async generateICPPrompt(data: {
    targetIndustries?: string[];
    targetJobTitles?: string[];
    targetCompanySizes?: string[];
    targetLocations?: string[];
    scoringCriteria?: Array<{name: string; weight: number}>;
    customRequirements?: string;
  }) {
    return this.client.post('/api/icp/generate-prompt', data);
  }

  // New ICP prompt endpoints
  async getICPPrompt() {
    try {
      const response = await this.client.get('/api/icp/prompt');
      // Normalize backend response. Some backends return:
      // { prompt: { status: 'success', data: { prompt: string, default_values: {...} } }, default_values: {...} }
      // We want to always return: { status: 'success', data: { prompt: string, default_values: {...} } }
      const raw = response.data as any;
      let prompt: string = '';
      let default_values: Record<string, any> | undefined = undefined;

      if (raw) {
        if (raw.prompt && typeof raw.prompt === 'object') {
          // Unwrap nested object
          const inner = raw.prompt.data || raw.prompt;
          prompt = inner.prompt || '';
          default_values = raw.default_values || inner.default_values || undefined;
        } else {
          prompt = raw.prompt || '';
          default_values = raw.default_values || undefined;
        }
      }

      return {
        status: 'success' as const,
        data: { prompt, default_values },
        message: 'ICP prompt retrieved successfully'
      };
    } catch (error: any) {
      console.error('Error getting ICP prompt:', error);
      return {
        status: 'error' as const,
        message: error.response?.data?.message || error.message || 'Failed to get ICP prompt'
      };
    }
  }

  async updateICPPrompt(data: {
    prompt: string;
    default_values?: Record<string, string>;
  }) {
    try {
      const response = await this.client.post('/api/icp/prompt', data);
      return {
        status: 'success',
        data: response.data,
        message: 'ICP prompt updated successfully'
      };
    } catch (error: any) {
      console.error('Error updating ICP prompt:', error);
      return {
        status: 'error',
        message: error.response?.data?.message || error.message || 'Failed to update ICP prompt'
      };
    }
  }

  // Legacy ICP endpoints for backward compatibility
  async getICPConfigurations() {
    return this.client.get('/api/icp/config');
  }

  async createICPConfiguration(data: {
    name: string;
    description?: string;
    criteria?: Record<string, any>;
    weights?: Record<string, number>;
    targetIndustries?: string[];
    targetRoles?: string[];
    companySizeRanges?: string[];
    geographicPreferences?: string[];
    technologyStack?: string[];
    minimumScoreThreshold?: number;
    isActive?: boolean;
  }) {
    return this.client.post('/api/icp/config', data);
  }

  async updateICPConfiguration(configId: string, data: Record<string, any>) {
    return this.client.post('/api/icp/config', data);
  }

  async deleteICPConfiguration(configId: string) {
    return this.client.delete(`/api/icp/config?id=${configId}`);
  }

  async scoreLeadAgainstICP(leadData: Record<string, any>, configId?: string) {
    return this.client.post('/api/icp/config', { action: 'score', leadData, configId });
  }

  async bulkScoreLeads(leadIds: string[], configId?: string) {
    return this.client.post('/api/icp/config', { action: 'bulk-score', leadIds, configId });
  }

  async getICPAnalytics(configId?: string, timeRange: string = '30d') {
    return this.client.get('/api/icp/config', { params: { action: 'analytics', configId, timeRange } });
  }

  // Webhook endpoints
  async handleEmailWebhook(webhookData: Record<string, any>) {
    return this.client.post('/api/webhook', webhookData);
  }

  // Configuration endpoints
  async getConfiguration() {
    return this.client.get('/api/configuration');
  }

  async getLeadGenerationConfig() {
    return this.client.get('/api/generate-leads');
  }

  async updateConfiguration(data: Record<string, any>) {
    return this.client.put('/api/config', data);
  }

  // Utility method for handling API responses
  static handleResponse<T>(response: AxiosResponse<T>): T {
    return response.data;
  }

  // Utility method for handling API errors
  static handleError(error: any): never {
    if (error.response) {
      // Server responded with error status
      const message = error.response.data?.message || error.response.statusText;
      throw new Error(`API Error: ${message}`);
    } else if (error.request) {
      // Request was made but no response received
      throw new Error('Network Error: No response from server');
    } else {
      // Something else happened
      throw new Error(`Request Error: ${error.message}`);
    }
  }
}

// Create and export a singleton instance
const apiClient = new ApiClient();
export default apiClient;

// Export the class for testing or custom instances
export { ApiClient };

// Export types for better TypeScript support
export interface ApiResponse<T = any> {
  status: 'success' | 'error';
  message?: string;
  data?: T;
}

export interface PaginatedResponse<T = any> {
  status: 'success' | 'error';
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
  total: number;
}

export interface Lead {
  id: string;
  full_name: string;
  email: string;
  job_title: string;
  company_name: string;
  company_industry: string;
  location: string;
  icp_score: number;
  icp_grade: string;
  source: string;
  email_status?: string;
  last_contacted?: string;
  created_at: string;
  updated_at: string;
}

export interface EmailTemplate {
  id: string;
  name: string;
  subject: string;
  body: string;
  type: string;
  variables: string[];
  created_at: string;
  updated_at: string;
}

export interface ICPConfiguration {
  id: string;
  name: string;
  description: string;
  criteria: Record<string, any>;
  weights: Record<string, number>;
  target_industries: string[];
  target_roles: string[];
  company_size_ranges: string[];
  geographic_preferences: string[];
  technology_stack: string[];
  minimum_score_threshold: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}