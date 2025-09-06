import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import OpenAI from 'openai'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
})

export async function POST(request: NextRequest) {
  try {
    // Get user from JWT token
    const authHeader = request.headers.get('authorization')
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return NextResponse.json(
        { status: 'error', message: 'Authentication required' },
        { status: 401 }
      )
    }

    const token = authHeader.substring(7)
    const { data: { user }, error: authError } = await supabase.auth.getUser(token)
    
    if (authError || !user) {
      return NextResponse.json(
        { status: 'error', message: 'Invalid authentication token' },
        { status: 401 }
      )
    }

    const userId = user.id
    
    const body = await request.json()
    const { 
      targetIndustries = [], 
      targetJobTitles = [], 
      targetCompanySizes = [], 
      targetLocations = [],
      scoringCriteria = [],
      customRequirements = ''
    } = body

    if (!process.env.OPENAI_API_KEY) {
      // Return a sample prompt when OpenAI API key is not configured
      const samplePrompt = `You are an AI assistant tasked with scoring leads based on their fit with our Ideal Customer Profile (ICP). 

Analyze the following lead profile: {profile_json}

Scoring Criteria:
${targetIndustries.length > 0 ? `- Industry Match (30%): Score based on alignment with target industries: ${targetIndustries.join(', ')}` : '- Industry Match (30%): Score based on industry relevance'}
${targetJobTitles.length > 0 ? `- Job Title Relevance (25%): Score based on decision-making authority for titles: ${targetJobTitles.join(', ')}` : '- Job Title Relevance (25%): Score based on decision-making authority'}
${targetCompanySizes.length > 0 ? `- Company Size (20%): Score based on company size match: ${targetCompanySizes.join(', ')} employees` : '- Company Size (20%): Score based on company size appropriateness'}
${targetLocations.length > 0 ? `- Geographic Location (15%): Score based on target locations: ${targetLocations.join(', ')}` : '- Geographic Location (15%): Score based on geographic accessibility'}
- Additional Criteria (10%): ${customRequirements || 'General business fit and potential'}

Provide your response in the following JSON format:
{
  "score": <number between 0-100>,
  "grade": "<A+, A, B+, B, C+, C, or D>",
  "reasoning": "<detailed explanation of the score>",
  "strengths": ["<list of positive factors>"],
  "concerns": ["<list of potential issues>"]
}

Grading Scale:
- A+ (90-100): Perfect fit, high priority lead
- A (80-89): Excellent fit, strong potential
- B+ (70-79): Good fit, moderate potential
- B (60-69): Acceptable fit, some potential
- C+ (50-59): Marginal fit, low potential
- C (40-49): Poor fit, very low potential
- D (0-39): Not a fit, no potential`

      return NextResponse.json({
        status: 'success',
        data: {
          prompt: samplePrompt,
          note: 'This is a sample prompt. To generate custom prompts with AI, please configure your OpenAI API key in the environment variables.'
        }
      })
    }

    const prompt = `Generate a comprehensive ICP (Ideal Customer Profile) scoring prompt for a lead generation system. The prompt should be used by AI to score leads from 0-100 based on how well they match the ideal customer profile.

Target Criteria:
- Industries: ${targetIndustries.length > 0 ? targetIndustries.join(', ') : 'Not specified'}
- Job Titles: ${targetJobTitles.length > 0 ? targetJobTitles.join(', ') : 'Not specified'}
- Company Sizes: ${targetCompanySizes.length > 0 ? targetCompanySizes.join(', ') : 'Not specified'}
- Locations: ${targetLocations.length > 0 ? targetLocations.join(', ') : 'Not specified'}
- Scoring Criteria: ${scoringCriteria.length > 0 ? scoringCriteria.map((c: { name: string; weight: number }) => `${c.name} (${c.weight}%)`).join(', ') : 'Standard criteria'}
- Additional Requirements: ${customRequirements || 'None specified'}

Please generate a detailed ICP scoring prompt that:
1. Uses the placeholder {profile_json} for lead data injection
2. Clearly defines the scoring criteria and weights
3. Specifies the exact JSON response format
4. Includes a grading scale (A+, A, B+, B, C+, C, D)
5. Provides clear instructions for scoring each criterion
6. Is professional and comprehensive

The prompt should be ready to use directly in an AI system for lead scoring.`

    const response = await openai.chat.completions.create({
      model: 'gpt-5-nano-2025-08-07',
      messages: [
        {
          role: 'system',
          content: 'You are an expert in creating AI prompts for lead scoring and ICP analysis. Generate clear, comprehensive prompts that will help AI systems accurately score leads.'
        },
        {
          role: 'user',
          content: prompt
        }
      ],
      max_tokens: 2000
    })

    const generatedPrompt = response.choices[0]?.message?.content

    if (!generatedPrompt) {
      return NextResponse.json(
        { status: 'error', message: 'Failed to generate prompt' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      status: 'success',
      data: {
        prompt: generatedPrompt
      }
    })

  } catch (error) {
    console.error('Error generating ICP prompt:', error)
    return NextResponse.json(
      { status: 'error', message: 'Failed to generate ICP prompt' },
      { status: 500 }
    )
  }
}