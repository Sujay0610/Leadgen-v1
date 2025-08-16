-- Create email_events table
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

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_email_events_event_type ON email_events(event_type);
CREATE INDEX IF NOT EXISTS idx_email_events_created_at ON email_events(created_at);
CREATE INDEX IF NOT EXISTS idx_email_events_email_id ON email_events(email_id);
CREATE INDEX IF NOT EXISTS idx_email_events_processed_at ON email_events(processed_at);

-- Enable RLS but allow service role to bypass
ALTER TABLE email_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_events FORCE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Allow authenticated users to read email events" ON email_events;
DROP POLICY IF EXISTS "Allow webhook service to insert email events" ON email_events;
DROP POLICY IF EXISTS "Allow webhook service to update email events" ON email_events;

-- Create a single policy for all operations (SELECT, INSERT, UPDATE)
CREATE POLICY "Allow service operations on email events"
ON email_events
FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

-- Create a view for email metrics
CREATE OR REPLACE VIEW email_metrics AS
WITH event_counts AS (
    SELECT
        COUNT(*) FILTER (WHERE event_type = 'email.sent') as total_sent,
        COUNT(*) FILTER (WHERE event_type = 'email.delivered') as total_delivered,
        COUNT(DISTINCT email_id) FILTER (WHERE event_type = 'email.opened') as unique_opens,
        SUM(opened_count) FILTER (WHERE event_type = 'email.opened') as total_opens,
        COUNT(DISTINCT email_id) FILTER (WHERE event_type = 'email.clicked') as unique_clicks,
        COUNT(*) FILTER (WHERE event_type = 'email.clicked') as total_clicks,
        COUNT(*) FILTER (WHERE event_type = 'email.bounced') as total_bounced,
        COUNT(*) FILTER (WHERE event_type = 'email.complained') as total_complained
    FROM email_events
)
SELECT
    total_sent,
    total_delivered,
    unique_opens,
    total_opens,
    unique_clicks,
    total_clicks,
    total_bounced,
    total_complained,
    ROUND(
        (total_delivered::FLOAT / NULLIF(total_sent, 0) * 100)::NUMERIC, 
        2
    ) as delivery_rate,
    ROUND(
        (unique_opens::FLOAT / NULLIF(total_delivered, 0) * 100)::NUMERIC, 
        2
    ) as unique_open_rate,
    ROUND(
        (total_opens::FLOAT / NULLIF(unique_opens, 0))::NUMERIC,
        2
    ) as opens_per_unique_open,
    ROUND(
        (unique_clicks::FLOAT / NULLIF(unique_opens, 0) * 100)::NUMERIC, 
        2
    ) as click_through_rate,
    ROUND(
        (total_bounced::FLOAT / NULLIF(total_sent, 0) * 100)::NUMERIC, 
        2
    ) as bounce_rate
FROM event_counts;

-- Create a view for time-based analytics
CREATE OR REPLACE VIEW email_time_metrics AS
SELECT
    date_trunc('hour', created_at) as time_bucket,
    COUNT(*) FILTER (WHERE event_type = 'email.sent') as sent_count,
    COUNT(*) FILTER (WHERE event_type = 'email.delivered') as delivered_count,
    COUNT(DISTINCT email_id) FILTER (WHERE event_type = 'email.opened') as unique_opens,
    SUM(opened_count) FILTER (WHERE event_type = 'email.opened') as total_opens,
    COUNT(DISTINCT email_id) FILTER (WHERE event_type = 'email.clicked') as unique_clicks,
    COUNT(*) FILTER (WHERE event_type = 'email.clicked') as total_clicks
FROM email_events
GROUP BY time_bucket
ORDER BY time_bucket; 