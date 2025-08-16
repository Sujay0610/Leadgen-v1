import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

// OpenAI Chat API integration
class ChatAPI {
  private apiKey: string

  constructor(apiKey: string) {
    this.apiKey = apiKey
  }

  async processQuery(userMessage: string, conversationHistory: any[] = []) {
    try {
      const systemPrompt = `
You are an AI assistant specialized in lead generation and prospecting. Your role is to help users find potential customers based on their requirements.

When a user asks for leads, analyze their request and extract:
1. Job titles/roles they're targeting
2. Industries they want to focus on
3. Geographic locations
4. Company sizes (if mentioned)
5. Any other specific criteria

If the user's request is clear enough to generate leads, respond with a JSON object in this format:
{
  "action": "generate_leads",
  "parameters": {
    "jobTitles": ["Operations Manager", "Facility Manager"],
    "industries": ["Manufacturing", "Healthcare"],
    "locations": ["United States", "Canada"],
    "companySizes": ["Medium", "Large"],
    "method": "apollo",
    "limit": 10
  },
  "message": "I'll search for Operations and Facility Managers in Manufacturing and Healthcare companies across the US and Canada."
}

If you need more information, respond with:
{
  "action": "clarify",
  "message": "I need more details about your target audience. What specific job titles or industries are you interested in?"
}

For general questions about lead generation, respond with:
{
  "action": "inform",
  "message": "Your helpful response here"
}

Always be helpful, professional, and focused on lead generation and sales prospecting.
`

      const messages = [
        { role: 'system', content: systemPrompt },
        ...conversationHistory,
        { role: 'user', content: userMessage }
      ]

      const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`
        },
        body: JSON.stringify({
          model: 'gpt-4',
          messages,
          temperature: 0.7,
          max_tokens: 1000
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

      // Try to parse as JSON first
      try {
        const jsonResponse = JSON.parse(content)
        return jsonResponse
      } catch {
        // If not JSON, treat as plain text response
        return {
          action: 'inform',
          message: content
        }
      }
    } catch (error) {
      console.error('Chat API error:', error)
      throw error
    }
  }
}

// Lead generation function (reused from generate-leads route)
async function generateLeads(parameters: any) {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/api/generate-leads`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(parameters)
    })

    if (!response.ok) {
      throw new Error(`Lead generation failed: ${response.status}`)
    }

    const data = await response.json()
    return data
  } catch (error) {
    console.error('Lead generation error:', error)
    throw error
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { message, conversationHistory = [] } = body

    if (!message) {
      return NextResponse.json(
        { status: 'error', message: 'Message is required' },
        { status: 400 }
      )
    }

    if (!process.env.OPENAI_API_KEY) {
      return NextResponse.json(
        { status: 'error', message: 'OpenAI API key not configured' },
        { status: 500 }
      )
    }

    const chatAPI = new ChatAPI(process.env.OPENAI_API_KEY)
    const response = await chatAPI.processQuery(message, conversationHistory)

    // If the AI wants to generate leads, do it
    if (response.action === 'generate_leads') {
      try {
        const leadResult = await generateLeads(response.parameters)
        
        if (leadResult.status === 'success') {
          return NextResponse.json({
            status: 'success',
            action: 'generate_leads',
            message: `${response.message} Found ${leadResult.count} leads!`,
            leads: leadResult.leads,
            count: leadResult.count
          })
        } else {
          return NextResponse.json({
            status: 'success',
            action: 'inform',
            message: `I tried to generate leads but encountered an issue: ${leadResult.message}. Please try refining your search criteria.`
          })
        }
      } catch (error) {
        console.error('Lead generation error in chat:', error)
        return NextResponse.json({
          status: 'success',
          action: 'inform',
          message: 'I encountered an error while generating leads. Please try again or contact support if the issue persists.'
        })
      }
    }

    // For other actions (clarify, inform), just return the response
    return NextResponse.json({
      status: 'success',
      action: response.action,
      message: response.message
    })

  } catch (error) {
    console.error('Chat API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}

// GET endpoint for chat history or status
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const action = searchParams.get('action')

    if (action === 'examples') {
      return NextResponse.json({
        status: 'success',
        examples: [
          "Find operations managers in manufacturing companies in Texas",
          "I need facility managers at healthcare organizations",
          "Show me plant managers in the automotive industry",
          "Find maintenance directors at large companies in California",
          "I'm looking for decision makers in food processing companies"
        ]
      })
    }

    if (action === 'capabilities') {
      return NextResponse.json({
        status: 'success',
        capabilities: {
          leadGeneration: true,
          apolloIntegration: !!process.env.APOLLO_API_KEY,
          googleSearch: !!process.env.GOOGLE_API_KEY,
          apifyEnrichment: !!process.env.APIFY_TOKEN,
          icpScoring: !!process.env.OPENAI_API_KEY,
          conversationalAI: !!process.env.OPENAI_API_KEY
        }
      })
    }

    return NextResponse.json(
      { status: 'error', message: 'Invalid action specified' },
      { status: 400 }
    )

  } catch (error) {
    console.error('Chat GET error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}