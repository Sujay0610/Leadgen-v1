-- Complete Database Setup with User Isolation for Lead Generation System
-- This migration creates all necessary tables and functions from scratch with user isolation
-- Run this on a fresh Supabase database after dropping all existing tables

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- LEADS TABLE - Core table for storing lead information with user isolation
-- =====================================================
CREATE TABLE IF NOT EXISTS leads (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    
    -- Basic profile information
    linkedin_url TEXT,
    full_name TEXT,
    first_name TEXT,
    last_name TEXT,
    headline TEXT,
    about TEXT,
    
    -- Contact information
    email TEXT,
    email_address TEXT,
    email_status TEXT,
    phone_number TEXT,
    
    -- Job information
    job_title TEXT,
    seniority TEXT,
    departments TEXT,
    subdepartments TEXT,
    functions TEXT,
    work_experience_months INTEGER,
    employment_history TEXT,
    
    -- Location information
    location TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    
    -- Company information
    company_name TEXT,
    company_website TEXT,
    company_domain TEXT,
    company_linkedin TEXT,
    company_twitter TEXT,
    company_facebook TEXT,
    company_phone TEXT,
    company_size TEXT,
    company_industry TEXT,
    company_founded_year INTEGER,
    company_growth_6month TEXT,
    company_growth_12month TEXT,
    company_growth_24month TEXT,
    
    -- Additional profile data
    photo_url TEXT,
    experience TEXT, -- JSON string of experiences
    
    -- Intent and engagement data
    intent_strength TEXT,
    show_intent BOOLEAN,
    email_domain_catchall BOOLEAN,
    revealed_for_current_team BOOLEAN,
    
    -- ICP scoring
    icp_score DECIMAL(5,2),
    icp_percentage DECIMAL(5,2),
    icp_grade TEXT,
    icp_breakdown TEXT, -- JSON string
    
    -- Email campaign status
    send_email_status TEXT DEFAULT 'Not Sent',
    
    -- Scraping metadata
    scraping_status TEXT,
    error_message TEXT,
    scraped_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint for user-specific LinkedIn URLs
    UNIQUE(user_id, linkedin_url)
);

-- Create indexes for leads table
CREATE INDEX IF NOT EXISTS idx_leads_user_id ON leads(user_id);
CREATE INDEX IF NOT EXISTS idx_leads_linkedin_url ON leads(linkedin_url);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_email_address ON leads(email_address);
CREATE INDEX IF NOT EXISTS idx_leads_full_name ON leads(full_name);
CREATE INDEX IF NOT EXISTS idx_leads_company_name ON leads(company_name);
CREATE INDEX IF NOT EXISTS idx_leads_job_title ON leads(job_title);
CREATE INDEX IF NOT EXISTS idx_leads_icp_score ON leads(icp_score);
CREATE INDEX IF NOT EXISTS idx_leads_icp_percentage ON leads(icp_percentage);
CREATE INDEX IF NOT EXISTS idx_leads_icp_grade ON leads(icp_grade);
CREATE INDEX IF NOT EXISTS idx_leads_scraping_status ON leads(scraping_status);
CREATE INDEX IF NOT EXISTS idx_leads_send_email_status ON leads(send_email_status);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);
CREATE INDEX IF NOT EXISTS idx_leads_scraped_at ON leads(scraped_at);
CREATE INDEX IF NOT EXISTS idx_leads_company_industry ON leads(company_industry);
CREATE INDEX IF NOT EXISTS idx_leads_company_size ON leads(company_size);

-- Add updated_at trigger for leads
CREATE TRIGGER update_leads_updated_at
    BEFORE UPDATE ON leads
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- EMAIL TEMPLATES TABLE - For storing email templates with vector embeddings and user isolation
-- =====================================================
CREATE TABLE IF NOT EXISTS email_templates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE, -- NULL for system templates
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    persona TEXT NOT NULL,  -- e.g., 'operations_manager', 'facility_manager'
    stage TEXT NOT NULL,    -- e.g., 'initial_outreach', 'follow_up'
    embedding vector(1536), -- OpenAI embedding dimension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for email_templates
CREATE INDEX IF NOT EXISTS idx_email_templates_user_id ON email_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_email_templates_persona_stage ON email_templates(persona, stage);
CREATE INDEX IF NOT EXISTS idx_email_templates_created_at ON email_templates(created_at);

-- Add updated_at trigger for email_templates
CREATE TRIGGER update_email_templates_updated_at
    BEFORE UPDATE ON email_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- EMAIL DRAFTS TABLE - For storing email drafts with user isolation
-- =====================================================
CREATE TABLE IF NOT EXISTS email_drafts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    persona TEXT,
    stage TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for email_drafts
CREATE INDEX IF NOT EXISTS idx_email_drafts_user_id ON email_drafts(user_id);
CREATE INDEX IF NOT EXISTS idx_email_drafts_lead_id ON email_drafts(lead_id);
CREATE INDEX IF NOT EXISTS idx_email_drafts_status ON email_drafts(status);
CREATE INDEX IF NOT EXISTS idx_email_drafts_persona_stage ON email_drafts(persona, stage);
CREATE INDEX IF NOT EXISTS idx_email_drafts_created_at ON email_drafts(created_at);

-- Add updated_at trigger for email_drafts
CREATE TRIGGER update_email_drafts_updated_at
    BEFORE UPDATE ON email_drafts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- EMAIL CAMPAIGNS TABLE - For managing email campaigns with user isolation
-- =====================================================
CREATE TABLE IF NOT EXISTS email_campaigns (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    persona TEXT,
    stage TEXT,
    target_criteria JSONB,
    scheduled_at TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for email_campaigns
CREATE INDEX IF NOT EXISTS idx_email_campaigns_user_id ON email_campaigns(user_id);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_status ON email_campaigns(status);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_persona_stage ON email_campaigns(persona, stage);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_scheduled_at ON email_campaigns(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_created_at ON email_campaigns(created_at);

-- Add updated_at trigger for email_campaigns
CREATE TRIGGER update_email_campaigns_updated_at
    BEFORE UPDATE ON email_campaigns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- EMAIL EVENTS TABLE - For tracking email events with user isolation
-- =====================================================
CREATE TABLE IF NOT EXISTS email_events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    event_type VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    email_id VARCHAR,
    from_email VARCHAR,
    to_email VARCHAR,
    subject VARCHAR,
    tags JSONB,
    raw_payload JSONB,
    
    -- Bounce-specific fields
    bounce_type VARCHAR,
    bounce_subtype VARCHAR,
    bounce_message TEXT,
    
    -- Click-specific fields
    click_ip VARCHAR,
    click_link VARCHAR,
    click_user_agent VARCHAR,
    click_timestamp TIMESTAMP WITH TIME ZONE,
    
    -- Open-specific fields
    opened_count INTEGER,
    first_opened_at TIMESTAMP WITH TIME ZONE,
    last_opened_at TIMESTAMP WITH TIME ZONE,
    device_info JSONB,
    location_info JSONB,
    
    -- Metadata
    inserted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for email_events
CREATE INDEX IF NOT EXISTS idx_email_events_user_id ON email_events(user_id);
CREATE INDEX IF NOT EXISTS idx_email_events_event_type ON email_events(event_type);
CREATE INDEX IF NOT EXISTS idx_email_events_created_at ON email_events(created_at);
CREATE INDEX IF NOT EXISTS idx_email_events_email_id ON email_events(email_id);
CREATE INDEX IF NOT EXISTS idx_email_events_processed_at ON email_events(processed_at);
CREATE INDEX IF NOT EXISTS idx_email_events_to_email ON email_events(to_email);

-- =====================================================
-- ICP_SETTINGS TABLE - For user-specific ICP configuration
-- =====================================================
CREATE TABLE IF NOT EXISTS icp_settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    target_industries TEXT[],
    target_job_titles TEXT[],
    target_company_sizes TEXT[],
    target_locations TEXT[],
    exclude_industries TEXT[],
    exclude_company_sizes TEXT[],
    min_employee_count INTEGER DEFAULT 0,
    max_employee_count INTEGER DEFAULT 10000,
    scoring_criteria JSONB DEFAULT '[]'::jsonb,
    custom_prompt TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Create indexes for icp_settings
CREATE INDEX IF NOT EXISTS idx_icp_settings_user_id ON icp_settings(user_id);

-- Add updated_at trigger for icp_settings
CREATE TRIGGER update_icp_settings_updated_at
    BEFORE UPDATE ON icp_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- CHAT_CONVERSATIONS TABLE - For user-specific chat history
-- =====================================================
CREATE TABLE IF NOT EXISTS chat_conversations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    title TEXT,
    messages JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for chat_conversations
CREATE INDEX IF NOT EXISTS idx_chat_conversations_user_id ON chat_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_created_at ON chat_conversations(created_at);

-- Add updated_at trigger for chat_conversations
CREATE TRIGGER update_chat_conversations_updated_at
    BEFORE UPDATE ON chat_conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- PROFILES TABLE - For user authentication and profiles
-- =====================================================
CREATE TABLE IF NOT EXISTS profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for profiles
CREATE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);
CREATE INDEX IF NOT EXISTS idx_profiles_role ON profiles(role);

-- Add updated_at trigger for profiles
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- VECTOR SIMILARITY SEARCH FUNCTION WITH USER ISOLATION
-- =====================================================
CREATE OR REPLACE FUNCTION match_email_templates(
    query_embedding vector(1536),
    match_threshold float,
    match_count int,
    user_id_param UUID DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    subject TEXT,
    body TEXT,
    persona TEXT,
    stage TEXT,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.id,
        t.subject,
        t.body,
        t.persona,
        t.stage,
        1 - (t.embedding <=> query_embedding) AS similarity
    FROM email_templates t
    WHERE 
        1 - (t.embedding <=> query_embedding) > match_threshold
        AND (
            user_id_param IS NULL 
            OR t.user_id = user_id_param 
            OR t.user_id IS NULL  -- Include system templates
        )
    ORDER BY t.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- =====================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE icp_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Policies for leads table - users can only access their own leads
CREATE POLICY "Users can view own leads" ON leads
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own leads" ON leads
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own leads" ON leads
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own leads" ON leads
    FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

-- Policies for email_templates table - users can only access their own templates
CREATE POLICY "Users can view own email templates" ON email_templates
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id OR user_id IS NULL); -- Allow access to system templates (user_id IS NULL)

CREATE POLICY "Users can insert own email templates" ON email_templates
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own email templates" ON email_templates
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own email templates" ON email_templates
    FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

-- Policies for email_drafts table - users can only access their own drafts
CREATE POLICY "Users can view own email drafts" ON email_drafts
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own email drafts" ON email_drafts
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own email drafts" ON email_drafts
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own email drafts" ON email_drafts
    FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

-- Policies for email_campaigns table - users can only access their own campaigns
CREATE POLICY "Users can view own email campaigns" ON email_campaigns
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own email campaigns" ON email_campaigns
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own email campaigns" ON email_campaigns
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own email campaigns" ON email_campaigns
    FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

-- Policies for email_events table - users can only access their own events
CREATE POLICY "Users can view own email events" ON email_events
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can insert email events" ON email_events
    FOR INSERT
    TO service_role
    WITH CHECK (true);

CREATE POLICY "Users can insert own email events" ON email_events
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

-- Policies for icp_settings table - users can only access their own settings
CREATE POLICY "Users can view own ICP settings" ON icp_settings
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own ICP settings" ON icp_settings
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own ICP settings" ON icp_settings
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own ICP settings" ON icp_settings
    FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

-- Policies for chat_conversations table - users can only access their own conversations
CREATE POLICY "Users can view own chat conversations" ON chat_conversations
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own chat conversations" ON chat_conversations
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own chat conversations" ON chat_conversations
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own chat conversations" ON chat_conversations
    FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

-- Policies for profiles table
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT
    TO authenticated
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can insert own profile" ON profiles
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = id);

-- =====================================================
-- FUNCTIONS FOR AUTOMATIC USER DATA INITIALIZATION
-- =====================================================

-- Function to initialize user data
CREATE OR REPLACE FUNCTION public.initialize_user_data(user_id_param UUID)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Create default ICP settings for new user
    INSERT INTO public.icp_settings (
        user_id,
        target_industries,
        target_job_titles,
        target_company_sizes,
        target_locations,
        min_employee_count,
        max_employee_count,
        custom_prompt
    ) VALUES (
        user_id_param,
        ARRAY['Technology', 'Healthcare', 'Finance'],
        ARRAY['Operations Manager', 'Facility Manager', 'Director of Operations'],
        ARRAY['51-200', '201-500', '501-1000'],
        ARRAY['United States', 'Canada'],
        50,
        1000,
        'Focus on companies that would benefit from facility management solutions.'
    )
    ON CONFLICT (user_id) DO NOTHING;
END;
$$;

-- Function to handle new user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
    -- Create user profile
    INSERT INTO public.profiles (id, email, full_name)
    VALUES (
        new.id,
        new.email,
        COALESCE(new.raw_user_meta_data->>'full_name', new.email)
    );
    
    -- Initialize user-specific data
    PERFORM public.initialize_user_data(new.id);
    
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger for automatic profile creation
CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- =====================================================
-- SAMPLE DATA (OPTIONAL)
-- =====================================================

-- Insert sample system email templates (user_id = NULL for system templates)
INSERT INTO email_templates (user_id, subject, body, persona, stage) VALUES
(NULL, 'Quick question about your operations', 'Hi {{first_name}},\n\nI noticed you''re managing operations at {{company_name}}. I''d love to learn more about your current challenges with facility management.\n\nWould you be open to a brief 15-minute call this week?\n\nBest regards,\n[Your Name]', 'operations_manager', 'initial_outreach'),
(NULL, 'Following up on our conversation', 'Hi {{first_name}},\n\nI wanted to follow up on my previous message about facility management solutions.\n\nMany operations managers like yourself have found our approach helpful for reducing costs and improving efficiency.\n\nWould you be interested in seeing a quick demo?\n\nBest,\n[Your Name]', 'operations_manager', 'follow_up')
ON CONFLICT DO NOTHING;

-- =====================================================
-- COMPLETION MESSAGE
-- =====================================================

-- Add a comment to indicate successful completion
COMMENT ON SCHEMA public IS 'Lead Generation Database - Complete Setup with User Isolation';

-- Display success message
SELECT 'Database setup completed successfully with user isolation!' AS status;