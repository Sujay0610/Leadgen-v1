-- Create table for storing ICP prompt configuration
CREATE TABLE IF NOT EXISTS icp_prompt_config (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    prompt TEXT NOT NULL,
    default_values JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_icp_prompt_config_updated_at ON icp_prompt_config(updated_at);

-- Add updated_at trigger
CREATE TRIGGER update_icp_prompt_config_updated_at
    BEFORE UPDATE ON icp_prompt_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default configuration if table is empty
INSERT INTO icp_prompt_config (prompt, default_values)
SELECT 
    'You are an expert lead qualification analyst. Analyze the following LinkedIn profile and score it based on how well it fits our Ideal Customer Profile (ICP).

Our ICP targets:
- {target_roles} (e.g., Operations managers, facility managers, maintenance managers)
- Companies in {target_industries} (e.g., manufacturing, industrial, automotive)
- {target_company_size} (e.g., Mid-size companies with 50-1000+ employees)
- {decision_maker_criteria} (e.g., Decision makers or influencers in operational processes)

Profile to analyze:
Name: {name}
Title: {title}
Company: {company}
Industry: {industry}
Company Size: {company_size}
Location: {location}
Headline: {headline}
Summary: {summary}

Please analyze this profile and provide a JSON response with the following structure:
{{
  "total_score": <float between 0-100>,
  "score_percentage": <integer between 0-100>,
  "grade": "<A/B/C/D>",
  "breakdown": {{
    "industry_fit": <float between 0-25>,
    "role_fit": <float between 0-25>,
    "company_size_fit": <float between 0-25>,
    "decision_maker": <float between 0-25>,
    "icp_category": "<operations/field_service/other>",
    "reasoning": "<brief explanation of the scoring>"
  }}
}}

Scoring criteria:
- Industry fit (0-25): How well does the company industry match our target sectors?
- Role fit (0-25): How relevant is their job title to our target roles?
- Company size fit (0-25): Does the company size align with our target market?
- Decision maker (0-25): Are they likely to influence or make purchasing decisions?',
    '{
        "target_roles": "Operations managers, facility managers, maintenance managers, and similar operational roles",
        "target_industries": "manufacturing, industrial, automotive, and related sectors",
        "target_company_size": "Mid-size companies (50-1000+ employees) that would benefit from operational efficiency solutions",
        "decision_maker_criteria": "Decision makers or influencers in operational processes"
    }'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM icp_prompt_config);