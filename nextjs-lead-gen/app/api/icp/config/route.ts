import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { randomUUID } from 'crypto'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

// Default ICP configuration
const DEFAULT_ICP_CONFIG = {
  scoringCriteria: {
    jobTitle: { enabled: true, weight: 25 },
    companySize: { enabled: true, weight: 20 },
    industry: { enabled: true, weight: 20 },
    location: { enabled: true, weight: 15 },
    experience: { enabled: true, weight: 10 },
    education: { enabled: false, weight: 5 },
    skills: { enabled: false, weight: 5 }
  },
  targetingRules: {
    industries: [
      'Manufacturing',
      'Industrial',
      'Automotive',
      'Aerospace',
      'Energy',
      'Chemical',
      'Food & Beverage',
      'Pharmaceutical'
    ],
    jobTitles: [
      'Operations Manager',
      'Facility Manager',
      'Maintenance Manager',
      'Plant Manager',
      'Production Manager',
      'Engineering Manager',
      'VP Operations',
      'Director of Operations'
    ],
    companySizes: [
      '51-200',
      '201-500',
      '501-1000',
      '1001-5000',
      '5000+'
    ],
    locations: [
      'United States',
      'Canada',
      'United Kingdom',
      'Germany',
      'France',
      'Australia'
    ]
  },
  customPrompt: `Analyze this lead profile and provide an ICP score from 0-100 based on how well they match our ideal customer profile.

Lead Profile:
- Name: {fullName}
- Job Title: {jobTitle}
- Company: {companyName}
- Industry: {industry}
- Location: {location}
- Company Size: {companySize}
- Experience: {experience}

Scoring Criteria:
- Job Title relevance (25%): How well does their role align with decision-making for operational efficiency solutions?
- Company Size (20%): Preference for mid to large companies (50+ employees)
- Industry (20%): Focus on manufacturing, industrial, and related sectors
- Location (15%): Geographic markets we serve
- Experience (10%): Years of relevant experience
- Education (5%): Relevant educational background
- Skills (5%): Technical and management skills

Provide your response in this exact JSON format:
{
  "score": 85,
  "grade": "A",
  "reasoning": "Detailed explanation of the score"
}

Grade Scale:
- A+ (95-100): Perfect match
- A (85-94): Excellent match
- B+ (75-84): Very good match
- B (65-74): Good match
- C+ (55-64): Fair match
- C (45-54): Below average match
- D+ (35-44): Poor match
- D (0-34): Very poor match`
}

export async function GET(request: NextRequest) {
  try {
    // Try to get existing configuration from database
    const { data: config, error } = await supabase
      .from('icp_config')
      .select('*')
      .single()

    if (error && error.code !== 'PGRST116') { // PGRST116 is "not found" error
      console.error('Error fetching ICP config:', error)
      return NextResponse.json(
        { status: 'error', message: 'Failed to fetch ICP configuration' },
        { status: 500 }
      )
    }

    // If no config exists, return default configuration
    const icpConfig = config ? {
      scoringCriteria: config.scoringCriteria || DEFAULT_ICP_CONFIG.scoringCriteria,
      targetingRules: config.targetingRules || DEFAULT_ICP_CONFIG.targetingRules,
      customPrompt: config.customPrompt || DEFAULT_ICP_CONFIG.customPrompt,
      updatedAt: config.updatedAt
    } : DEFAULT_ICP_CONFIG

    // Get statistics
    const stats = await getICPStatistics()

    return NextResponse.json({
      status: 'success',
      config: icpConfig,
      statistics: stats
    })

  } catch (error) {
    console.error('ICP config GET API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { scoringCriteria, targetingRules, customPrompt } = body

    if (!scoringCriteria && !targetingRules && !customPrompt) {
      return NextResponse.json(
        { status: 'error', message: 'At least one configuration section is required' },
        { status: 400 }
      )
    }

    // Validate scoring criteria weights sum to 100
    if (scoringCriteria) {
      const totalWeight = Object.values(scoringCriteria)
        .filter((criteria: any) => criteria.enabled)
        .reduce((sum: number, criteria: any) => sum + criteria.weight, 0)

      if (totalWeight !== 100) {
        return NextResponse.json(
          { status: 'error', message: `Enabled criteria weights must sum to 100. Current total: ${totalWeight}` },
          { status: 400 }
        )
      }
    }

    // Check if configuration already exists
    const { data: existingConfig } = await supabase
      .from('icp_config')
      .select('id')
      .single()

    const configData = {
      scoringCriteria: scoringCriteria || DEFAULT_ICP_CONFIG.scoringCriteria,
      targetingRules: targetingRules || DEFAULT_ICP_CONFIG.targetingRules,
      customPrompt: customPrompt || DEFAULT_ICP_CONFIG.customPrompt,
      updatedAt: new Date().toISOString()
    }

    let result
    if (existingConfig) {
      // Update existing configuration
      result = await supabase
        .from('icp_config')
        .update(configData)
        .eq('id', existingConfig.id)
        .select()
        .single()
    } else {
      // Create new configuration
      result = await supabase
          .from('icp_config')
          .insert({
            id: randomUUID(),
          ...configData,
          createdAt: new Date().toISOString()
        })
        .select()
        .single()
    }

    if (result.error) {
      console.error('Error saving ICP config:', result.error)
      return NextResponse.json(
        { status: 'error', message: 'Failed to save ICP configuration' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      status: 'success',
      message: 'ICP configuration saved successfully',
      config: result.data
    })

  } catch (error) {
    console.error('ICP config POST API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json()
    const { action } = body

    if (action === 'reset') {
      // Reset to default configuration
      const { data: existingConfig } = await supabase
        .from('icp_config')
        .select('id')
        .single()

      const configData = {
        ...DEFAULT_ICP_CONFIG,
        updatedAt: new Date().toISOString()
      }

      let result
      if (existingConfig) {
        result = await supabase
          .from('icp_config')
          .update(configData)
          .eq('id', existingConfig.id)
          .select()
          .single()
      } else {
        result = await supabase
          .from('icp_config')
          .insert({
            id: randomUUID(),
            ...configData,
            createdAt: new Date().toISOString()
          })
          .select()
          .single()
      }

      if (result.error) {
        console.error('Error resetting ICP config:', result.error)
        return NextResponse.json(
          { status: 'error', message: 'Failed to reset ICP configuration' },
          { status: 500 }
        )
      }

      return NextResponse.json({
        status: 'success',
        message: 'ICP configuration reset to defaults',
        config: result.data
      })
    }

    return NextResponse.json(
      { status: 'error', message: 'Invalid action specified' },
      { status: 400 }
    )

  } catch (error) {
    console.error('ICP config PUT API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}

// Helper function to get ICP statistics
async function getICPStatistics() {
  try {
    // Get all leads with ICP scores
    const { data: leads, error } = await supabase
      .from('leads')
      .select('icpScore, icpGrade')
      .not('icpScore', 'is', null)

    if (error) {
      console.error('Error fetching leads for statistics:', error)
      return {
        totalLeads: 0,
        averageScore: 0,
        gradeDistribution: {
          'A+': 0, 'A': 0, 'B+': 0, 'B': 0,
          'C+': 0, 'C': 0, 'D+': 0, 'D': 0
        }
      }
    }

    const totalLeads = leads?.length || 0
    const averageScore = totalLeads > 0 
      ? Math.round((leads.reduce((sum, lead) => sum + (lead.icpScore || 0), 0) / totalLeads) * 100) / 100
      : 0

    // Calculate grade distribution
    const gradeDistribution = {
      'A+': 0, 'A': 0, 'B+': 0, 'B': 0,
      'C+': 0, 'C': 0, 'D+': 0, 'D': 0
    }

    leads?.forEach(lead => {
      const grade = lead.icpGrade
      if (grade && gradeDistribution.hasOwnProperty(grade)) {
        gradeDistribution[grade as keyof typeof gradeDistribution]++
      }
    })

    return {
      totalLeads,
      averageScore,
      gradeDistribution
    }
  } catch (error) {
    console.error('Error calculating ICP statistics:', error)
    return {
      totalLeads: 0,
      averageScore: 0,
      gradeDistribution: {
        'A+': 0, 'A': 0, 'B+': 0, 'B': 0,
        'C+': 0, 'C': 0, 'D+': 0, 'D': 0
      }
    }
  }
}