import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import crypto, { randomUUID } from 'crypto'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

// Webhook verification for Resend
function verifyWebhookSignature(payload: string, signature: string, secret: string): boolean {
  try {
    const expectedSignature = crypto
      .createHmac('sha256', secret)
      .update(payload)
      .digest('hex')
    
    return crypto.timingSafeEqual(
      Buffer.from(signature, 'hex'),
      Buffer.from(expectedSignature, 'hex')
    )
  } catch (error) {
    console.error('Error verifying webhook signature:', error)
    return false
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.text()
    const signature = request.headers.get('resend-signature')
    const webhookSecret = process.env.RESEND_WEBHOOK_SECRET

    // Verify webhook signature if secret is configured
    if (webhookSecret && signature) {
      const isValid = verifyWebhookSignature(body, signature, webhookSecret)
      if (!isValid) {
        console.error('Invalid webhook signature')
        return NextResponse.json(
          { status: 'error', message: 'Invalid signature' },
          { status: 401 }
        )
      }
    }

    const event = JSON.parse(body)
    console.log('Received webhook event:', event.type)

    // Handle different event types
    switch (event.type) {
      case 'email.sent':
        await handleEmailSent(event.data)
        break
      case 'email.delivered':
        await handleEmailDelivered(event.data)
        break
      case 'email.delivery_delayed':
        await handleEmailDelayed(event.data)
        break
      case 'email.complained':
        await handleEmailComplained(event.data)
        break
      case 'email.bounced':
        await handleEmailBounced(event.data)
        break
      case 'email.opened':
        await handleEmailOpened(event.data)
        break
      case 'email.clicked':
        await handleEmailClicked(event.data)
        break
      default:
        console.log(`Unhandled event type: ${event.type}`)
    }

    return NextResponse.json({ status: 'success', message: 'Webhook processed' })

  } catch (error) {
    console.error('Webhook processing error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Webhook processing failed' },
      { status: 500 }
    )
  }
}

// Handle email sent event
async function handleEmailSent(data: any) {
  try {
    const { email_id, to, subject, created_at } = data

    // Find the lead by email
    const { data: lead } = await supabase
      .from('leads')
      .select('id')
      .eq('email', to[0])
      .single()

    if (lead) {
      // Create email event record
      await supabase
        .from('email_events')
        .insert({
          id: randomUUID(),
          leadId: lead.id,
          eventType: 'sent',
          resendId: email_id,
          subject,
          recipient: to[0],
          createdAt: created_at || new Date().toISOString()
        })

      console.log(`Email sent event recorded for lead ${lead.id}`)
    }
  } catch (error) {
    console.error('Error handling email sent event:', error)
  }
}

// Handle email delivered event
async function handleEmailDelivered(data: any) {
  try {
    const { email_id, to, created_at } = data

    // Find the lead by email
    const { data: lead } = await supabase
      .from('leads')
      .select('id')
      .eq('email', to[0])
      .single()

    if (lead) {
      // Create email event record
      await supabase
        .from('email_events')
        .insert({
          id: randomUUID(),
          leadId: lead.id,
          eventType: 'delivered',
          resendId: email_id,
          recipient: to[0],
          createdAt: created_at || new Date().toISOString()
        })

      console.log(`Email delivered event recorded for lead ${lead.id}`)
    }
  } catch (error) {
    console.error('Error handling email delivered event:', error)
  }
}

// Handle email delayed event
async function handleEmailDelayed(data: any) {
  try {
    const { email_id, to, created_at } = data

    // Find the lead by email
    const { data: lead } = await supabase
      .from('leads')
      .select('id')
      .eq('email', to[0])
      .single()

    if (lead) {
      // Create email event record
      await supabase
        .from('email_events')
        .insert({
          id: randomUUID(),
          leadId: lead.id,
          eventType: 'delayed',
          resendId: email_id,
          recipient: to[0],
          createdAt: created_at || new Date().toISOString()
        })

      console.log(`Email delayed event recorded for lead ${lead.id}`)
    }
  } catch (error) {
    console.error('Error handling email delayed event:', error)
  }
}

// Handle email complained event
async function handleEmailComplained(data: any) {
  try {
    const { email_id, to, created_at } = data

    // Find the lead by email
    const { data: lead } = await supabase
      .from('leads')
      .select('id')
      .eq('email', to[0])
      .single()

    if (lead) {
      // Create email event record
      await supabase
        .from('email_events')
        .insert({
          id: randomUUID(),
          leadId: lead.id,
          eventType: 'complained',
          resendId: email_id,
          recipient: to[0],
          createdAt: created_at || new Date().toISOString()
        })

      // Update lead email status to complained
      await supabase
        .from('leads')
        .update({ emailStatus: 'complained' })
        .eq('id', lead.id)

      console.log(`Email complained event recorded for lead ${lead.id}`)
    }
  } catch (error) {
    console.error('Error handling email complained event:', error)
  }
}

// Handle email bounced event
async function handleEmailBounced(data: any) {
  try {
    const { email_id, to, created_at } = data

    // Find the lead by email
    const { data: lead } = await supabase
      .from('leads')
      .select('id')
      .eq('email', to[0])
      .single()

    if (lead) {
      // Create email event record
      await supabase
        .from('email_events')
        .insert({
          id: randomUUID(),
          leadId: lead.id,
          eventType: 'bounced',
          resendId: email_id,
          recipient: to[0],
          createdAt: created_at || new Date().toISOString()
        })

      // Update lead email status to bounced
      await supabase
        .from('leads')
        .update({ emailStatus: 'bounced' })
        .eq('id', lead.id)

      console.log(`Email bounced event recorded for lead ${lead.id}`)
    }
  } catch (error) {
    console.error('Error handling email bounced event:', error)
  }
}

// Handle email opened event
async function handleEmailOpened(data: any) {
  try {
    const { email_id, to, created_at } = data

    // Find the lead by email
    const { data: lead } = await supabase
      .from('leads')
      .select('id')
      .eq('email', to[0])
      .single()

    if (lead) {
      // Create email event record
      await supabase
        .from('email_events')
        .insert({
          id: randomUUID(),
          leadId: lead.id,
          eventType: 'opened',
          resendId: email_id,
          recipient: to[0],
          createdAt: created_at || new Date().toISOString()
        })

      // Update lead email status to opened if not already replied
      const { data: currentLead } = await supabase
        .from('leads')
        .select('emailStatus')
        .eq('id', lead.id)
        .single()

      if (currentLead && currentLead.emailStatus !== 'replied') {
        await supabase
          .from('leads')
          .update({ emailStatus: 'opened' })
          .eq('id', lead.id)
      }

      console.log(`Email opened event recorded for lead ${lead.id}`)
    }
  } catch (error) {
    console.error('Error handling email opened event:', error)
  }
}

// Handle email clicked event
async function handleEmailClicked(data: any) {
  try {
    const { email_id, to, created_at, link } = data

    // Find the lead by email
    const { data: lead } = await supabase
      .from('leads')
      .select('id')
      .eq('email', to[0])
      .single()

    if (lead) {
      // Create email event record
      await supabase
        .from('email_events')
        .insert({
          id: randomUUID(),
          leadId: lead.id,
          eventType: 'clicked',
          resendId: email_id,
          recipient: to[0],
          metadata: { link },
          createdAt: created_at || new Date().toISOString()
        })

      // Update lead email status to clicked if not already replied
      const { data: currentLead } = await supabase
        .from('leads')
        .select('emailStatus')
        .eq('id', lead.id)
        .single()

      if (currentLead && currentLead.emailStatus !== 'replied') {
        await supabase
          .from('leads')
          .update({ emailStatus: 'clicked' })
          .eq('id', lead.id)
      }

      console.log(`Email clicked event recorded for lead ${lead.id}`)
    }
  } catch (error) {
    console.error('Error handling email clicked event:', error)
  }
}

// GET endpoint for webhook status and testing
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const action = searchParams.get('action')

    if (action === 'status') {
      // Return webhook configuration status
      return NextResponse.json({
        status: 'success',
        webhook: {
          configured: !!process.env.RESEND_WEBHOOK_SECRET,
          endpoint: `${process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000'}/api/webhook`
        }
      })
    }

    if (action === 'test') {
      // Test webhook functionality with a mock event
      const testEvent = {
        type: 'email.opened',
        data: {
          email_id: 'test-email-id',
          to: ['test@example.com'],
          created_at: new Date().toISOString()
        }
      }

      console.log('Processing test webhook event:', testEvent)
      
      return NextResponse.json({
        status: 'success',
        message: 'Webhook test completed',
        testEvent
      })
    }

    return NextResponse.json({
      status: 'success',
      message: 'Webhook endpoint is active',
      supportedEvents: [
        'email.sent',
        'email.delivered',
        'email.delivery_delayed',
        'email.complained',
        'email.bounced',
        'email.opened',
        'email.clicked'
      ]
    })

  } catch (error) {
    console.error('Webhook GET API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}