-- Create email_drafts table
CREATE TABLE IF NOT EXISTS email_drafts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    persona TEXT,
    stage TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add comments
COMMENT ON TABLE email_drafts IS 'Stores email drafts that can be used as templates';
COMMENT ON COLUMN email_drafts.lead_id IS 'Identifier for the lead (typically LinkedIn URL)';
COMMENT ON COLUMN email_drafts.subject IS 'Email subject line';
COMMENT ON COLUMN email_drafts.body IS 'Email body content';
COMMENT ON COLUMN email_drafts.status IS 'Status of the draft (draft, sent, template)';
COMMENT ON COLUMN email_drafts.persona IS 'Target persona for the email (e.g., operations_manager)';
COMMENT ON COLUMN email_drafts.stage IS 'Email stage (e.g., initial_outreach, follow_up)';

-- Create indexes for faster retrieval
CREATE INDEX IF NOT EXISTS email_drafts_lead_id_idx ON email_drafts (lead_id);
CREATE INDEX IF NOT EXISTS email_drafts_status_idx ON email_drafts (status);
CREATE INDEX IF NOT EXISTS email_drafts_persona_stage_idx ON email_drafts (persona, stage);

-- Set up RLS (Row Level Security)
ALTER TABLE email_drafts ENABLE ROW LEVEL SECURITY;

-- Create policy for full access with service role
CREATE POLICY email_drafts_service_role_policy ON email_drafts 
    USING (auth.role() = 'service_role');

-- Create trigger to update the updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_email_drafts_updated_at
BEFORE UPDATE ON email_drafts
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column(); 