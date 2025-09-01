-- Migration: Add User Isolation to Lead Generation System
-- This migration adds user_id columns and updates RLS policies for proper user data isolation
-- Run this after the initial database setup

-- =====================================================
-- ADD USER_ID COLUMNS TO EXISTING TABLES
-- =====================================================

-- Add user_id to leads table
ALTER TABLE leads ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- Add user_id to email_templates table
ALTER TABLE email_templates ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- Add user_id to email_drafts table
ALTER TABLE email_drafts ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- Add user_id to email_campaigns table
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- Add user_id to email_events table (for tracking user-specific events)
ALTER TABLE email_events ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- =====================================================
-- CREATE INDEXES FOR USER_ID COLUMNS
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_leads_user_id ON leads(user_id);
CREATE INDEX IF NOT EXISTS idx_email_templates_user_id ON email_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_email_drafts_user_id ON email_drafts(user_id);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_user_id ON email_campaigns(user_id);
CREATE INDEX IF NOT EXISTS idx_email_events_user_id ON email_events(user_id);

-- =====================================================
-- CREATE ICP_SETTINGS TABLE FOR USER-SPECIFIC ICP CONFIGURATION
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
-- CREATE CHAT_CONVERSATIONS TABLE FOR USER-SPECIFIC CHAT HISTORY
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
-- DROP EXISTING RLS POLICIES
-- =====================================================

-- Drop existing policies for leads
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON leads;
DROP POLICY IF EXISTS "Enable insert/update for authenticated users" ON leads;

-- Drop existing policies for email_templates
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON email_templates;
DROP POLICY IF EXISTS "Enable insert/update for authenticated users" ON email_templates;

-- Drop existing policies for email_drafts
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON email_drafts;
DROP POLICY IF EXISTS "Enable insert/update for authenticated users" ON email_drafts;

-- Drop existing policies for email_campaigns
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON email_campaigns;
DROP POLICY IF EXISTS "Enable insert/update for authenticated users" ON email_campaigns;

-- Drop existing policies for email_events
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON email_events;

-- =====================================================
-- CREATE NEW USER-ISOLATED RLS POLICIES
-- =====================================================

-- Enable RLS on new tables
ALTER TABLE icp_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_conversations ENABLE ROW LEVEL SECURITY;

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

-- =====================================================
-- UPDATE VECTOR SIMILARITY SEARCH FUNCTION FOR USER ISOLATION
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
-- CREATE FUNCTION TO INITIALIZE USER DATA
-- =====================================================

CREATE OR REPLACE FUNCTION initialize_user_data(user_id_param UUID)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Create default ICP settings for new user
    INSERT INTO icp_settings (
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

-- =====================================================
-- UPDATE USER SIGNUP TRIGGER
-- =====================================================

-- Update the handle_new_user function to initialize user data
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
    PERFORM initialize_user_data(new.id);
    
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- COMPLETION MESSAGE
-- =====================================================

-- Add a comment to indicate successful completion
COMMENT ON SCHEMA public IS 'Lead Generation Database - User Isolation Migration Complete';