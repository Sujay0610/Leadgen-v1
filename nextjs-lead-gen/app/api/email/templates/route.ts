import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { randomUUID } from 'crypto'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

// OpenAI integration for template generation
class TemplateGenerator {
  private apiKey: string

  constructor(apiKey: string) {
    this.apiKey = apiKey
  }

  async generateTemplate(persona: string, stage: string, leadData: any) {
    try {
      const prompt = this.buildPrompt(persona, stage, leadData)

      const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`
        },
        body: JSON.stringify({
          model: 'gpt-5-nano-2025-08-07',
          messages: [{ role: 'user', content: prompt }],
          max_tokens: 500
        })
      })

      if (!response.ok) {
        throw new Error(`OpenAI API error: ${response.status}`)
      }

      const data = await response.json()
      const content = data.choices[0]?.message?.content

      if (!content) {
        throw new Error('No content in OpenAI response')
      }

      const result = JSON.parse(content)
      return {
        subject: result.subject || 'Follow up',
        body: result.body || 'Hello, I wanted to follow up with you.'
      }
    } catch (error) {
      console.error('Template generation error:', error)
      throw error
    }
  }

  private buildPrompt(persona: string, stage: string, leadData: any): string {
    const personaContext = this.getPersonaContext(persona)
    const stageContext = this.getStageContext(stage)

    return `
Generate a professional email template for the following context:

Persona: ${persona} (${personaContext})
Stage: ${stage} (${stageContext})

Lead Information:
- Name: ${leadData.fullName || 'N/A'}
- First Name: ${leadData.firstName || 'N/A'}
- Job Title: ${leadData.jobTitle || 'N/A'}
- Company: ${leadData.companyName || 'N/A'}
- Email: ${leadData.email || 'N/A'}

Requirements:
1. Professional and personalized tone
2. Relevant to the persona and stage
3. Include specific value proposition
4. Clear call-to-action
5. Keep it concise (under 150 words)
6. Use the lead's first name and company name

Respond with ONLY a JSON object in this format:
{
  "subject": "Email subject line",
  "body": "Email body content with proper formatting"
}
`
  }

  private getPersonaContext(persona: string): string {
    const contexts = {
      operations_manager: 'Focuses on operational efficiency, cost reduction, and process optimization',
      facility_manager: 'Responsible for building maintenance, safety, and facility operations',
      maintenance_manager: 'Oversees equipment maintenance, reliability, and asset management',
      plant_manager: 'Manages overall plant operations, production, and team leadership'
    }
    return contexts[persona as keyof typeof contexts] || 'General business professional'
  }

  private getStageContext(stage: string): string {
    const contexts = {
      initial_outreach: 'First contact to introduce yourself and your value proposition',
      follow_up: 'Following up on previous communication or meeting',
      meeting_request: 'Requesting a meeting or demo to discuss solutions'
    }
    return contexts[stage as keyof typeof contexts] || 'General business communication'
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const persona = searchParams.get('persona')
    const stage = searchParams.get('stage')
    const limit = parseInt(searchParams.get('limit') || '50')

    let query = supabase
      .from('email_templates')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(limit)

    if (persona) {
      query = query.eq('persona', persona)
    }

    if (stage) {
      query = query.eq('stage', stage)
    }

    const { data: templates, error } = await query

    if (error) {
      console.error('Error fetching templates:', error)
      return NextResponse.json(
        { status: 'error', message: 'Failed to fetch templates' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      status: 'success',
      templates: templates || []
    })

  } catch (error) {
    console.error('Templates GET API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { action } = body

    if (action === 'generate') {
      const { persona, stage, leadData } = body

      if (!persona || !stage || !leadData) {
        return NextResponse.json(
          { status: 'error', message: 'Persona, stage, and lead data are required for generation' },
          { status: 400 }
        )
      }

      if (!process.env.OPENAI_API_KEY) {
        return NextResponse.json(
          { status: 'error', message: 'OpenAI API key not configured' },
          { status: 500 }
        )
      }

      try {
        const generator = new TemplateGenerator(process.env.OPENAI_API_KEY)
        const template = await generator.generateTemplate(persona, stage, leadData)

        return NextResponse.json({
          status: 'success',
          subject: template.subject,
          body: template.body
        })
      } catch (error) {
        console.error('Template generation error:', error)
        return NextResponse.json(
          { status: 'error', message: 'Failed to generate template' },
          { status: 500 }
        )
      }
    }

    if (action === 'save') {
      const { leadId, subject, body: emailBody, persona, stage } = body

      if (!subject || !emailBody || !persona || !stage) {
        return NextResponse.json(
          { status: 'error', message: 'Subject, body, persona, and stage are required' },
          { status: 400 }
        )
      }

      const templateData = {
        id: randomUUID(),
        subject,
        body: emailBody,
        persona,
        stage,
        leadId: leadId || null,
        usageCount: 0,
        createdAt: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }

      const { error } = await supabase
        .from('email_templates')
        .insert(templateData)

      if (error) {
        console.error('Error saving template:', error)
        return NextResponse.json(
          { status: 'error', message: 'Failed to save template' },
          { status: 500 }
        )
      }

      return NextResponse.json({
        status: 'success',
        message: 'Template saved successfully',
        templateId: templateData.id
      })
    }

    if (action === 'use') {
      const { templateId } = body

      if (!templateId) {
        return NextResponse.json(
          { status: 'error', message: 'Template ID is required' },
          { status: 400 }
        )
      }

      // Get current template to increment usage count
      const { data: template, error: fetchError } = await supabase
        .from('email_templates')
        .select('usage_count')
        .eq('id', templateId)
        .single()

      if (fetchError) {
        console.error('Error fetching template:', fetchError)
        return NextResponse.json(
          { status: 'error', message: 'Failed to fetch template' },
          { status: 500 }
        )
      }

      // Increment usage count
      const { error } = await supabase
        .from('email_templates')
        .update({
          usage_count: (template.usage_count || 0) + 1,
          updated_at: new Date().toISOString()
        })
        .eq('id', templateId)

      if (error) {
        console.error('Error updating template usage:', error)
        return NextResponse.json(
          { status: 'error', message: 'Failed to update template usage' },
          { status: 500 }
        )
      }

      return NextResponse.json({
        status: 'success',
        message: 'Template usage updated'
      })
    }

    return NextResponse.json(
      { status: 'error', message: 'Invalid action specified' },
      { status: 400 }
    )

  } catch (error) {
    console.error('Templates POST API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json()
    const { id, subject, body: templateBody, persona, stage } = body

    if (!id) {
      return NextResponse.json(
        { status: 'error', message: 'Template ID is required' },
        { status: 400 }
      )
    }

    const updateData: any = {
        updated_at: new Date().toISOString()
    }

    if (subject) updateData.subject = subject
    if (templateBody) updateData.body = templateBody
    if (persona) updateData.persona = persona
    if (stage) updateData.stage = stage

    const { data, error } = await supabase
      .from('email_templates')
      .update(updateData)
      .eq('id', id)
      .select()
      .single()

    if (error) {
      console.error('Error updating template:', error)
      return NextResponse.json(
        { status: 'error', message: 'Failed to update template' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      status: 'success',
      message: 'Template updated successfully',
      template: data
    })

  } catch (error) {
    console.error('Templates PUT API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const id = searchParams.get('id')

    if (!id) {
      return NextResponse.json(
        { status: 'error', message: 'Template ID is required' },
        { status: 400 }
      )
    }

    const { error } = await supabase
      .from('email_templates')
      .delete()
      .eq('id', id)

    if (error) {
      console.error('Error deleting template:', error)
      return NextResponse.json(
        { status: 'error', message: 'Failed to delete template' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      status: 'success',
      message: 'Template deleted successfully'
    })

  } catch (error) {
    console.error('Templates DELETE API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}