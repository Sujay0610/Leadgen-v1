-- Add missing columns to email_campaigns table
-- These columns are used in the frontend but missing from the current schema

ALTER TABLE public.email_campaigns 
ADD COLUMN IF NOT EXISTS open_rate numeric(5,2) DEFAULT 0.00,
ADD COLUMN IF NOT EXISTS reply_rate numeric(5,2) DEFAULT 0.00,
ADD COLUMN IF NOT EXISTS sent_count integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS scheduled_count integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_leads integer DEFAULT 0;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_email_campaigns_open_rate ON public.email_campaigns USING btree (open_rate);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_reply_rate ON public.email_campaigns USING btree (reply_rate);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_sent_count ON public.email_campaigns USING btree (sent_count);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_scheduled_count ON public.email_campaigns USING btree (scheduled_count);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_total_leads ON public.email_campaigns USING btree (total_leads);

-- Add comments for documentation
COMMENT ON COLUMN public.email_campaigns.open_rate IS 'Email open rate percentage (0.00 to 100.00)';
COMMENT ON COLUMN public.email_campaigns.reply_rate IS 'Email reply rate percentage (0.00 to 100.00)';
COMMENT ON COLUMN public.email_campaigns.sent_count IS 'Number of emails sent in this campaign';
COMMENT ON COLUMN public.email_campaigns.scheduled_count IS 'Number of emails scheduled to be sent';
COMMENT ON COLUMN public.email_campaigns.total_leads IS 'Total number of leads in this campaign';