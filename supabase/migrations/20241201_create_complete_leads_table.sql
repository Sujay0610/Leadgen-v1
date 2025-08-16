-- Complete leads table migration with all required fields
-- This migration creates a comprehensive leads table that matches the application requirements
-- Use this if you want to recreate the table from scratch

-- Drop the existing table if it exists (uncomment the line below if you want to recreate)
-- DROP TABLE IF EXISTS leads CASCADE;

-- Create the complete leads table with all required columns
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

-- Create indexes for performance
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
CREATE INDEX IF NOT EXISTS idx_leads_location ON leads(location);
CREATE INDEX IF NOT EXISTS idx_leads_city ON leads(city);
CREATE INDEX IF NOT EXISTS idx_leads_state ON leads(state);
CREATE INDEX IF NOT EXISTS idx_leads_country ON leads(country);

-- Enable RLS
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;

-- Create policies for access control
CREATE POLICY leads_service_role_policy ON leads 
    FOR ALL 
    TO service_role 
    USING (true) 
    WITH CHECK (true);

CREATE POLICY leads_authenticated_read_policy ON leads 
    FOR SELECT 
    TO authenticated 
    USING (true);

CREATE POLICY leads_authenticated_insert_policy ON leads 
    FOR INSERT 
    TO authenticated 
    WITH CHECK (true);

CREATE POLICY leads_authenticated_update_policy ON leads 
    FOR UPDATE 
    TO authenticated 
    USING (true) 
    WITH CHECK (true);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_leads_updated_at 
    BEFORE UPDATE ON leads 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create a view for commonly used lead data
CREATE OR REPLACE VIEW leads_summary AS
SELECT 
    id,
    linkedin_url,
    full_name,
    first_name,
    last_name,
    email,
    email_address,
    job_title,
    headline,
    company_name,
    company_industry,
    company_size,
    location,
    city,
    state,
    country,
    about,
    icp_score,
    icp_percentage,
    icp_grade,
    scraping_status,
    send_email_status,
    created_at,
    scraped_at,
    updated_at
FROM leads
ORDER BY created_at DESC;

-- Grant permissions on the view
GRANT SELECT ON leads_summary TO authenticated;
GRANT SELECT ON leads_summary TO service_role;

-- Create a view for ICP analytics
CREATE OR REPLACE VIEW leads_icp_analytics AS
SELECT 
    icp_grade,
    COUNT(*) as count,
    AVG(icp_percentage) as avg_percentage,
    MIN(icp_percentage) as min_percentage,
    MAX(icp_percentage) as max_percentage,
    COUNT(CASE WHEN send_email_status = 'Sent' THEN 1 END) as emails_sent,
    COUNT(CASE WHEN send_email_status = 'Not Sent' THEN 1 END) as emails_not_sent
FROM leads 
WHERE icp_grade IS NOT NULL
GROUP BY icp_grade
ORDER BY avg_percentage DESC;

-- Grant permissions on the analytics view
GRANT SELECT ON leads_icp_analytics TO authenticated;
GRANT SELECT ON leads_icp_analytics TO service_role;

-- Add comments to document the table structure
COMMENT ON TABLE leads IS 'Main table for storing lead information from LinkedIn profiles';
COMMENT ON COLUMN leads.linkedin_url IS 'Unique LinkedIn profile URL';
COMMENT ON COLUMN leads.about IS 'LinkedIn profile about/summary section';
COMMENT ON COLUMN leads.experience IS 'JSON string of work experiences from LinkedIn';
COMMENT ON COLUMN leads.employment_history IS 'JSON string of employment history';
COMMENT ON COLUMN leads.icp_breakdown IS 'JSON string containing detailed ICP scoring breakdown';
COMMENT ON COLUMN leads.scraping_status IS 'Status of the scraping process (success, error, no_data)';
COMMENT ON COLUMN leads.send_email_status IS 'Status of email sending (Not Sent, Sent, Failed, etc.)';
COMMENT ON COLUMN leads.scraped_at IS 'Timestamp when the profile was scraped';
COMMENT ON COLUMN leads.created_at IS 'Timestamp when the record was created';
COMMENT ON COLUMN leads.updated_at IS 'Timestamp when the record was last updated';