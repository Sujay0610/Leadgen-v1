-- Add default ICP settings for the system
-- This ensures there's always a fallback configuration available

INSERT INTO icp_settings (
    id,
    user_id,
    target_industries,
    target_job_titles,
    target_company_sizes,
    target_locations,
    exclude_industries,
    exclude_company_sizes,
    min_employee_count,
    max_employee_count,
    scoring_criteria,
    custom_prompt,
    created_at,
    updated_at
) VALUES (
    gen_random_uuid(),
    'default',
    ARRAY['Manufacturing', 'Industrial', 'Automotive', 'Technology', 'Healthcare'],
    ARRAY['Operations Manager', 'Facility Manager', 'Maintenance Manager', 'Plant Manager', 'Production Manager', 'COO', 'VP Operations'],
    ARRAY['51-200', '201-500', '501-1000', '1001-5000'],
    ARRAY['United States', 'Canada', 'United Kingdom', 'Germany', 'India'],
    ARRAY[],
    ARRAY[],
    50,
    10000,
    '[]'::jsonb,
    'You are an expert lead qualification analyst. Analyze the LinkedIn profile and score based on industry fit, role relevance, company size, and decision-making authority.',
    NOW(),
    NOW()
) ON CONFLICT (user_id) DO UPDATE SET
    target_industries = EXCLUDED.target_industries,
    target_job_titles = EXCLUDED.target_job_titles,
    target_company_sizes = EXCLUDED.target_company_sizes,
    target_locations = EXCLUDED.target_locations,
    updated_at = NOW();