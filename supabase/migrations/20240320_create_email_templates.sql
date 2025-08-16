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

-- Create email_drafts table
CREATE TABLE IF NOT EXISTS email_drafts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    lead_id TEXT NOT NULL,  -- Using LinkedIn URL as lead_id
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
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
CREATE INDEX IF NOT EXISTS email_drafts_lead_id_idx ON email_drafts(lead_id);

-- Enable Row Level Security (RLS)
ALTER TABLE email_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_drafts ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Enable read access for all users" ON email_templates
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Enable insert for authenticated users" ON email_templates
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

CREATE POLICY "Enable read access for all users" ON email_drafts
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Enable insert/update for authenticated users" ON email_drafts
    FOR ALL
    TO authenticated
    USING (true)
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

CREATE TRIGGER update_email_drafts_updated_at
    BEFORE UPDATE ON email_drafts
    FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column(); 