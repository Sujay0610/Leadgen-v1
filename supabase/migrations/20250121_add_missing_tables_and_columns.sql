-- Add missing started_at column and other missing columns to email_campaigns table
ALTER TABLE public.email_campaigns 
ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS email_interval INTEGER DEFAULT 24,
ADD COLUMN IF NOT EXISTS daily_limit INTEGER DEFAULT 50,
ADD COLUMN IF NOT EXISTS send_time_start TEXT DEFAULT '07:00',
ADD COLUMN IF NOT EXISTS send_time_end TEXT DEFAULT '09:00',
ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'America/New_York',
ADD COLUMN IF NOT EXISTS selected_leads JSONB,
ADD COLUMN IF NOT EXISTS template_id UUID REFERENCES email_templates(id),
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS open_rate numeric(5,2) DEFAULT 0.00,
ADD COLUMN IF NOT EXISTS reply_rate numeric(5,2) DEFAULT 0.00,
ADD COLUMN IF NOT EXISTS sent_count integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS scheduled_count integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_leads integer DEFAULT 0;

-- Create the missing scheduled_emails table
CREATE TABLE IF NOT EXISTS public.scheduled_emails (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    campaign_id UUID REFERENCES email_campaigns(id) ON DELETE CASCADE NOT NULL,
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE NOT NULL,
    to_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled', -- 'scheduled', 'sent', 'failed'
    sent_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    resend_id TEXT, -- ID from Resend service
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for email_campaigns
CREATE INDEX IF NOT EXISTS idx_email_campaigns_started_at ON public.email_campaigns USING btree (started_at);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_template_id ON public.email_campaigns USING btree (template_id);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_daily_limit ON public.email_campaigns USING btree (daily_limit);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_email_interval ON public.email_campaigns USING btree (email_interval);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_open_rate ON public.email_campaigns USING btree (open_rate);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_reply_rate ON public.email_campaigns USING btree (reply_rate);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_sent_count ON public.email_campaigns USING btree (sent_count);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_scheduled_count ON public.email_campaigns USING btree (scheduled_count);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_total_leads ON public.email_campaigns USING btree (total_leads);

-- Create indexes for scheduled_emails
CREATE INDEX IF NOT EXISTS idx_scheduled_emails_campaign_id ON public.scheduled_emails USING btree (campaign_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_emails_lead_id ON public.scheduled_emails USING btree (lead_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_emails_status ON public.scheduled_emails USING btree (status);
CREATE INDEX IF NOT EXISTS idx_scheduled_emails_scheduled_at ON public.scheduled_emails USING btree (scheduled_at);
CREATE INDEX IF NOT EXISTS idx_scheduled_emails_to_email ON public.scheduled_emails USING btree (to_email);

-- Add updated_at trigger for scheduled_emails
CREATE TRIGGER update_scheduled_emails_updated_at
    BEFORE UPDATE ON public.scheduled_emails
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON COLUMN public.email_campaigns.started_at IS 'Timestamp when the campaign was started';
COMMENT ON COLUMN public.email_campaigns.email_interval IS 'Interval between emails in hours';
COMMENT ON COLUMN public.email_campaigns.daily_limit IS 'Maximum number of emails to send per day';
COMMENT ON COLUMN public.email_campaigns.send_time_start IS 'Start time for sending emails (HH:MM format)';
COMMENT ON COLUMN public.email_campaigns.send_time_end IS 'End time for sending emails (HH:MM format)';
COMMENT ON COLUMN public.email_campaigns.timezone IS 'Timezone for scheduling emails';
COMMENT ON COLUMN public.email_campaigns.selected_leads IS 'JSON array of lead IDs for this campaign';
COMMENT ON COLUMN public.email_campaigns.template_id IS 'Reference to the email template used';
COMMENT ON COLUMN public.email_campaigns.description IS 'Campaign description';
COMMENT ON COLUMN public.email_campaigns.open_rate IS 'Email open rate percentage (0.00 to 100.00)';
COMMENT ON COLUMN public.email_campaigns.reply_rate IS 'Email reply rate percentage (0.00 to 100.00)';
COMMENT ON COLUMN public.email_campaigns.sent_count IS 'Number of emails sent in this campaign';
COMMENT ON COLUMN public.email_campaigns.scheduled_count IS 'Number of emails scheduled to be sent';
COMMENT ON COLUMN public.email_campaigns.total_leads IS 'Total number of leads in this campaign';

COMMENT ON TABLE public.scheduled_emails IS 'Table for storing scheduled emails for campaigns';
COMMENT ON COLUMN public.scheduled_emails.campaign_id IS 'Reference to the email campaign';
COMMENT ON COLUMN public.scheduled_emails.lead_id IS 'Reference to the lead receiving the email';
COMMENT ON COLUMN public.scheduled_emails.to_email IS 'Email address to send to';
COMMENT ON COLUMN public.scheduled_emails.scheduled_at IS 'When the email should be sent';
COMMENT ON COLUMN public.scheduled_emails.status IS 'Status of the scheduled email (scheduled, sent, failed)';
COMMENT ON COLUMN public.scheduled_emails.resend_id IS 'ID from Resend email service';

-- Add RLS policies for scheduled_emails
ALTER TABLE public.scheduled_emails ENABLE ROW LEVEL SECURITY;

-- Users can view scheduled emails for their own campaigns
CREATE POLICY "Users can view own scheduled emails" ON public.scheduled_emails
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM email_campaigns 
            WHERE email_campaigns.id = scheduled_emails.campaign_id 
            AND email_campaigns.user_id = auth.uid()
        )
    );

-- Users can insert scheduled emails for their own campaigns
CREATE POLICY "Users can insert own scheduled emails" ON public.scheduled_emails
    FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM email_campaigns 
            WHERE email_campaigns.id = scheduled_emails.campaign_id 
            AND email_campaigns.user_id = auth.uid()
        )
    );

-- Users can update scheduled emails for their own campaigns
CREATE POLICY "Users can update own scheduled emails" ON public.scheduled_emails
    FOR UPDATE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM email_campaigns 
            WHERE email_campaigns.id = scheduled_emails.campaign_id 
            AND email_campaigns.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM email_campaigns 
            WHERE email_campaigns.id = scheduled_emails.campaign_id 
            AND email_campaigns.user_id = auth.uid()
        )
    );

-- Service role can manage all scheduled emails (for background processing)
CREATE POLICY "Service role can manage scheduled emails" ON public.scheduled_emails
    FOR ALL
    TO service_role
    WITH CHECK (true);