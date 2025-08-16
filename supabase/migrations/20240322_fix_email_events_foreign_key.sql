-- Add lead_id column to email_events table to establish relationship with leads
ALTER TABLE email_events ADD COLUMN IF NOT EXISTS lead_id TEXT;

-- Create index for the new lead_id column
CREATE INDEX IF NOT EXISTS idx_email_events_lead_id ON email_events(lead_id);

-- Add foreign key constraint to link email_events to leads
-- Note: This assumes leads table has an 'id' column of type TEXT
-- If the leads table uses a different primary key, adjust accordingly
ALTER TABLE email_events 
ADD CONSTRAINT fk_email_events_lead_id 
FOREIGN KEY (lead_id) 
REFERENCES leads(id) 
ON DELETE CASCADE;

-- Update existing email_events to link them to leads based on email addresses
-- This is a best-effort attempt to link existing records
UPDATE email_events 
SET lead_id = leads.id 
FROM leads 
WHERE email_events.to_email = leads.email 
AND email_events.lead_id IS NULL;

-- Create a view to easily query email events with lead information
CREATE OR REPLACE VIEW email_events_with_leads AS
SELECT 
    ee.*,
    l.full_name,
    l.company_name,
    l.job_title,
    l.icp_percentage,
    l.email_status
FROM email_events ee
LEFT JOIN leads l ON ee.lead_id = l.id;