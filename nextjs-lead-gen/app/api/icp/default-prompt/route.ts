import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    // Return the default prompt that matches the backend implementation
    const defaultPrompt = `You are an ICP (Ideal Customer Profile) evaluator.

Your task is to assess how well this LinkedIn profile matches our target ICP criteria using the structured fields available.

Profile Data:
{profile_json}

Target ICP Criteria:

- Target Industries: {target_industries}
- Target Roles: {target_roles}
- Target Company Sizes: {target_company_sizes}
- Target Locations: {target_locations}
- Target Seniority: {target_seniority}

Scoring Criteria (each 0–10):
- industry_fit: Match between 'companyIndustry' and target industries
- role_fit: Match between 'jobTitle' or 'headline' and target roles
- company_size_fit: Match between 'companySize' and target company sizes
- decision_maker: Based on 'seniority', 'functions', or leadership keywords in relation to target seniority

Scoring Weights:
- industry_fit: 30%
- role_fit: 30%
- company_size_fit: 20%
- decision_maker: 20%

Instructions:
- Evaluate each criterion based on how well the profile matches the target criteria
- Use strict logic; if match is weak or unclear, give lower scores
- Calculate total_score as weighted average of the four criteria
- Determine icp_category: "high_fit" (score ≥ 7), "medium_fit" (score 4-6.9), or "low_fit" (score < 4)
- Output ONLY valid JSON (no extra explanation, markdown, or text)

Output Format:
{
    "industry_fit": <0-10>,
    "role_fit": <0-10>,
    "company_size_fit": <0-10>,
    "decision_maker": <0-10>,
    "total_score": <weighted avg score>,
    "icp_category": "high_fit" | "medium_fit" | "low_fit",
    "reasoning": "Brief reasoning based on the fields provided"
}`

    const defaultValues = {
      target_roles: 'Operations managers, facility managers, maintenance managers, plant managers, production engineers, digital transformation officers',
      target_industries: 'Manufacturing, Industrial Automation, Heavy Equipment, CNC, Robotics, Facility Management, Fleet Operations',
      target_company_sizes: 'Mid-size companies (50-1000+ employees), Enterprise companies (1000+ employees)',
      target_locations: 'North America, Europe, Global markets',
      target_seniority: 'Manager level and above, Director level, VP level, C-level executives'
    }

    return NextResponse.json({
      prompt: defaultPrompt,
      default_values: defaultValues
    })
  } catch (error) {
    console.error('Error getting default prompt:', error)
    return NextResponse.json(
      { error: 'Failed to get default prompt' },
      { status: 500 }
    )
  }
}