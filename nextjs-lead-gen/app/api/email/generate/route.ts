import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

class EmailGenerator {
  private apiKey: string

  constructor(apiKey: string) {
    this.apiKey = apiKey
  }

  async generateEmail(leadData: any) {
    try {
      const prompt = this.buildPrompt(leadData)

      const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`,
          'HTTP-Referer': process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000',
          'X-Title': 'Lead Generation Email System'
        },
        body: JSON.stringify({
          model: 'gpt-5-nano-2025-08-07',
          messages: [{ role: 'user', content: prompt }],
          max_tokens: 500
        })
      })

      if (!response.ok) {
        throw new Error(`OpenRouter API error: ${response.status}`)
      }

      const data = await response.json()
      const content = data.choices[0]?.message?.content

      if (!content) {
        throw new Error('No content in API response')
      }

      const result = JSON.parse(content)
      return {
        subject: result.subject || `Quick question about ${leadData.leadCompany}`,
        body: result.body || this.getFallbackEmail(leadData),
        status: 'success'
      }
    } catch (error) {
      console.error('Email generation error:', error)
      // Return fallback email instead of throwing
      return {
        subject: `Quick question about ${leadData.leadCompany}`,
        body: this.getFallbackEmail(leadData),
        status: 'success',
        fallback: true
      }
    }
  }

  private buildPrompt(leadData: any): string {
    return `
Generate a professional cold email for the following lead:

Lead Information:
- Name: ${leadData.leadName || 'N/A'}
- Job Title: ${leadData.leadTitle || 'N/A'}
- Company: ${leadData.leadCompany || 'N/A'}
- Email Type: ${leadData.emailType || 'cold_outreach'}
- Tone: ${leadData.tone || 'professional'}
- Custom Context: ${leadData.customContext || 'N/A'}

Requirements:
1. Professional and personalized tone
2. Reference specific details about the lead
3. Focus on operational efficiency and automation
4. Include a clear but soft call-to-action
5. Keep it concise (under 150 words)
6. Use the lead's name and company name

Respond with ONLY a JSON object in this format:
{
  "subject": "Email subject line",
  "body": "Email body content with proper formatting"
}
`
  }

  private getFallbackEmail(leadData: any): string {
    const firstName = leadData.leadName?.split(' ')[0] || 'there'
    const company = leadData.leadCompany || 'your company'
    
    return `Hi ${firstName},

I noticed ${company} is in the ${leadData.leadTitle || 'operations'} space. We help companies like yours streamline operations and reduce manual processes.

Many of our clients have seen significant improvements in efficiency and cost savings after implementing our automation solutions.

Would you be open to a brief conversation about how we could help ${company} improve operational efficiency?

Best regards,
Your Name`
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { leadName, leadCompany, leadTitle, emailType, tone, customContext } = body

    if (!leadName) {
      return NextResponse.json(
        { status: 'error', message: 'Lead name is required' },
        { status: 400 }
      )
    }

    // Check if OpenAI API key is available
    const apiKey = process.env.OPENAI_API_KEY
    if (!apiKey) {
      // Return fallback email if no API key
      const generator = new EmailGenerator('')
      const fallbackResult = {
        subject: `Quick question about ${leadCompany}`,
        body: generator['getFallbackEmail'](body),
        status: 'success',
        fallback: true
      }
      
      return NextResponse.json(fallbackResult)
    }

    const generator = new EmailGenerator(apiKey)
    const result = await generator.generateEmail({
      leadName,
      leadCompany,
      leadTitle,
      emailType,
      tone,
      customContext
    })

    // Log the generation for analytics
    try {
      await supabase
        .from('email_events')
        .insert({
          event_type: 'email_generated',
          lead_name: leadName,
          company_name: leadCompany,
          metadata: {
            emailType,
            tone,
            fallback: result.fallback || false
          },
          timestamp: new Date().toISOString()
        })
    } catch (logError) {
      console.error('Failed to log email generation:', logError)
      // Don't fail the request if logging fails
    }

    return NextResponse.json(result)

  } catch (error) {
    console.error('Email generation API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const action = searchParams.get('action')

    if (action === 'status') {
      // Return email generation service status
      return NextResponse.json({
        status: 'success',
        service: {
          available: true,
          aiEnabled: !!process.env.OPENAI_API_KEY,
          fallbackEnabled: true,
          supportedTypes: ['cold_outreach', 'follow_up', 'introduction'],
          supportedTones: ['professional', 'casual', 'friendly', 'formal']
        }
      })
    }

    if (action === 'templates') {
      // Return available email generation templates
      const templates = [
        {
          id: 'cold_outreach',
          name: 'Cold Outreach',
          description: 'Initial contact with potential leads'
        },
        {
          id: 'follow_up',
          name: 'Follow Up',
          description: 'Follow up on previous conversations'
        },
        {
          id: 'introduction',
          name: 'Introduction',
          description: 'Warm introduction emails'
        }
      ]

      return NextResponse.json({
        status: 'success',
        templates
      })
    }

    return NextResponse.json(
      { status: 'error', message: 'Invalid action specified' },
      { status: 400 }
    )

  } catch (error) {
    console.error('Email generation GET API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}