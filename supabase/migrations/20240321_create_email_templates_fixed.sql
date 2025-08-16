-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create email_templates table with vector embeddings
CREATE TABLE IF NOT EXISTS email_templates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    persona TEXT NOT NULL,  -- e.g., 'operations_manager', 'facility_manager'
    stage TEXT NOT NULL,    -- e.g., 'initial_outreach', 'follow_up'
    embedding vector(1536), -- OpenAI embedding dimension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create function for similarity search
CREATE OR REPLACE FUNCTION match_email_templates(
    query_embedding vector(1536),
    match_threshold float,
    match_count int
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
        1 - (t.embedding <=> query_embedding) as similarity
    FROM email_templates t
    WHERE 1 - (t.embedding <=> query_embedding) > match_threshold
    ORDER BY t.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Create indexes
CREATE INDEX IF NOT EXISTS email_templates_embedding_idx ON email_templates USING ivfflat (embedding vector_cosine_ops);

-- Enable Row Level Security (RLS)
ALTER TABLE email_templates ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Enable read access for all users" ON email_templates
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Enable insert for authenticated users" ON email_templates
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- Create trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_email_templates_updated_at
    BEFORE UPDATE ON email_templates
    FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column();

-- Insert some sample email templates
INSERT INTO email_templates (subject, body, persona, stage) VALUES
('Introduction - Facility Management Solutions', 'Hi {{full_name}},\n\nI hope this message finds you well. I noticed your role as {{job_title}} at {{company_name}} and wanted to reach out regarding our facility management solutions.\n\nWe help companies like yours optimize their operations and reduce costs through innovative facility management strategies.\n\nWould you be interested in a brief 15-minute call to discuss how we might be able to help {{company_name}}?\n\nBest regards,\n[Your Name]', 'facility_manager', 'initial_outreach'),
('Follow-up - Operations Efficiency', 'Hi {{full_name}},\n\nI wanted to follow up on my previous message about facility management solutions for {{company_name}}.\n\nMany operations managers like yourself have found our approach particularly valuable for streamlining processes and reducing overhead costs.\n\nWould next week work for a quick conversation?\n\nBest,\n[Your Name]', 'operations_manager', 'follow_up'),
('Cost Reduction Opportunities', 'Hello {{full_name}},\n\nAs {{job_title}} at {{company_name}}, you likely face ongoing pressure to optimize operational costs while maintaining service quality.\n\nOur recent case study with a similar company in {{company_industry}} showed a 25% reduction in facility-related expenses within the first quarter.\n\nI\'d love to share some insights that might be relevant to your situation. Are you available for a brief call this week?\n\nRegards,\n[Your Name]', 'facility_manager', 'initial_outreach');