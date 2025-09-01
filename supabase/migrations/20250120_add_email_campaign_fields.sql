-- Add missing fields to email_campaigns table
-- This migration adds the fields that the backend expects but are missing from the schema

ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS email_interval INTEGER DEFAULT 24;
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS daily_limit INTEGER DEFAULT 50;
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS send_time_start TEXT DEFAULT '07:00';
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS send_time_end TEXT DEFAULT '09:00';
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'America/New_York';
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS selected_leads JSONB;
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS template_id UUID REFERENCES email_templates(id);
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS description TEXT;

-- Create indexes for the new columns
CREATE INDEX IF NOT EXISTS idx_email_campaigns_template_id ON email_campaigns(template_id);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_daily_limit ON email_campaigns(daily_limit);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_email_interval ON email_campaigns(email_interval);

-- Add comments for documentation
COMMENT ON COLUMN email_campaigns.email_interval IS 'Interval between emails in hours';
COMMENT ON COLUMN email_campaigns.daily_limit IS 'Maximum number of emails to send per day';
COMMENT ON COLUMN email_campaigns.send_time_start IS 'Start time for sending emails (HH:MM format)';
COMMENT ON COLUMN email_campaigns.send_time_end IS 'End time for sending emails (HH:MM format)';
COMMENT ON COLUMN email_campaigns.timezone IS 'Timezone for scheduling emails';
COMMENT ON COLUMN email_campaigns.selected_leads IS 'JSON array of lead IDs for this campaign';
COMMENT ON COLUMN email_campaigns.template_id IS 'Reference to the email template used';
COMMENT ON COLUMN email_campaigns.description IS 'Campaign description';