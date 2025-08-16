-- Complete Database Setup for Lead Generation System
-- This migration creates all necessary tables and functions from scratch
-- Run this on a fresh Supabase database

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
-- LEADS TABLE - Core table for storing lead information
-- =====================================================
CREATE TABLE IF NOT EXISTS leads (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    
    -- Basic profile information
    linkedin_url TEXT UNIQUE,
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
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for leads table
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
-- EMAIL TEMPLATES TABLE - For storing email templates with vector embeddings
-- =====================================================
CREATE TABLE IF NOT EXISTS email_templates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    persona TEXT NOT NULL,  -- e.g., 'operations_manager', 'facility_manager'
    stage TEXT NOT NULL,    -- e.g., 'initial_outreach', 'follow_up'
    embedding vector(1536), -- OpenAI embedding dimension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for email_templates
CREATE INDEX IF NOT EXISTS idx_email_templates_persona_stage ON email_templates(persona, stage);
CREATE INDEX IF NOT EXISTS idx_email_templates_created_at ON email_templates(created_at);

-- Add updated_at trigger for email_templates
CREATE TRIGGER update_email_templates_updated_at
    BEFORE UPDATE ON email_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- EMAIL DRAFTS TABLE - For storing email drafts
-- =====================================================
CREATE TABLE IF NOT EXISTS email_drafts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
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
-- EMAIL CAMPAIGNS TABLE - For managing email campaigns
-- =====================================================
CREATE TABLE IF NOT EXISTS email_campaigns (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
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
-- EMAIL EVENTS TABLE - For tracking email events (opens, clicks, bounces)
-- =====================================================
CREATE TABLE IF NOT EXISTS email_events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
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
CREATE INDEX IF NOT EXISTS idx_email_events_event_type ON email_events(event_type);
CREATE INDEX IF NOT EXISTS idx_email_events_created_at ON email_events(created_at);
CREATE INDEX IF NOT EXISTS idx_email_events_email_id ON email_events(email_id);
CREATE INDEX IF NOT EXISTS idx_email_events_processed_at ON email_events(processed_at);
CREATE INDEX IF NOT EXISTS idx_email_events_to_email ON email_events(to_email);

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
-- VECTOR SIMILARITY SEARCH FUNCTION
-- =====================================================
CREATE OR REPLACE FUNCTION match_email_templates(
    query_embedding vector(1536),
    match_threshold float,
    match_count int
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
    WHERE 1 - (t.embedding <=> query_embedding) > match_threshold
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
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Policies for leads table
CREATE POLICY "Enable read access for authenticated users" ON leads
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Enable insert/update for authenticated users" ON leads
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Policies for email_templates table
CREATE POLICY "Enable read access for authenticated users" ON email_templates
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Enable insert/update for authenticated users" ON email_templates
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Policies for email_drafts table
CREATE POLICY "Enable read access for authenticated users" ON email_drafts
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Enable insert/update for authenticated users" ON email_drafts
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Policies for email_campaigns table
CREATE POLICY "Enable read access for authenticated users" ON email_campaigns
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Enable insert/update for authenticated users" ON email_campaigns
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Policies for email_events table
CREATE POLICY "Enable read access for authenticated users" ON email_events
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Enable insert for service role" ON email_events
    FOR INSERT
    TO service_role
    WITH CHECK (true);

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
-- FUNCTIONS FOR AUTOMATIC PROFILE CREATION
-- =====================================================

-- Function to handle new user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.profiles (id, email, full_name)
    VALUES (
        new.id,
        new.email,
        COALESCE(new.raw_user_meta_data->>'full_name', new.email)
    );
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

-- Insert sample email templates
INSERT INTO email_templates (subject, body, persona, stage) VALUES
('Quick question about your operations', 'Hi {{first_name}},\n\nI noticed you''re managing operations at {{company_name}}. I''d love to learn more about your current challenges with facility management.\n\nWould you be open to a brief 15-minute call this week?\n\nBest regards,\n[Your Name]', 'operations_manager', 'initial_outreach'),
('Following up on our conversation', 'Hi {{first_name}},\n\nI wanted to follow up on my previous message about facility management solutions.\n\nMany operations managers like yourself have found our approach helpful for reducing costs and improving efficiency.\n\nWould you be interested in seeing a quick demo?\n\nBest,\n[Your Name]', 'operations_manager', 'follow_up')
ON CONFLICT DO NOTHING;

-- =====================================================
-- COMPLETION MESSAGE
-- =====================================================

-- Add a comment to indicate successful completion
COMMENT ON SCHEMA public IS 'Lead Generation Database - Setup Complete';