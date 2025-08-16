-- Create email_campaigns table
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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS email_campaigns_status_idx ON email_campaigns(status);
CREATE INDEX IF NOT EXISTS email_campaigns_persona_stage_idx ON email_campaigns(persona, stage);
CREATE INDEX IF NOT EXISTS email_campaigns_scheduled_at_idx ON email_campaigns(scheduled_at);

-- Enable Row Level Security (RLS)
ALTER TABLE email_campaigns ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Enable read access for all users" ON email_campaigns
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Enable insert/update for authenticated users" ON email_campaigns
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Create trigger for updated_at
CREATE TRIGGER update_email_campaigns_updated_at
    BEFORE UPDATE ON email_campaigns
    FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column();

-- Fix email_drafts foreign key relationship
ALTER TABLE email_drafts 
ADD CONSTRAINT fk_email_drafts_lead_id 
FOREIGN KEY (lead_id) 
REFERENCES leads(id) 
ON DELETE CASCADE;

-- Create index for better performance
CREATE INDEX IF NOT EXISTS email_drafts_lead_id_fk_idx ON email_drafts(lead_id);