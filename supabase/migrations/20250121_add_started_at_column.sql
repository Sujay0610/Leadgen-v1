-- Add missing started_at column to email_campaigns table
-- This column is used when starting campaigns to track when they were started

ALTER TABLE public.email_campaigns 
ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITH TIME ZONE;

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_email_campaigns_started_at ON public.email_campaigns USING btree (started_at);

-- Add comment for documentation
COMMENT ON COLUMN public.email_campaigns.started_at IS 'Timestamp when the campaign was started';