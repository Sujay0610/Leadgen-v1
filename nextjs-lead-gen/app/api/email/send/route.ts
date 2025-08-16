import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { Resend } from 'resend'
import { randomUUID } from 'crypto'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

const resend = new Resend(process.env.RESEND_API_KEY)

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { to, subject, body: emailBody, leadId, leadData } = body

    if (!to || !subject || !emailBody) {
      return NextResponse.json(
        { status: 'error', message: 'To, subject, and body are required' },
        { status: 400 }
      )
    }

    if (!process.env.RESEND_API_KEY) {
      return NextResponse.json(
        { status: 'error', message: 'Email service not configured' },
        { status: 500 }
      )
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(to)) {
      return NextResponse.json(
        { status: 'error', message: 'Invalid email address format' },
        { status: 400 }
      )
    }

    try {
      // Send email using Resend
      const emailResult = await resend.emails.send({
        from: process.env.FROM_EMAIL || 'noreply@yourdomain.com',
        to: [to],
        subject: subject,
        html: `
          <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
              <h2 style="color: #333; margin: 0 0 10px 0;">${subject}</h2>
            </div>
            
            <div style="background-color: white; padding: 20px; border-radius: 8px; border: 1px solid #e9ecef;">
              ${emailBody.replace(/\n/g, '<br>')}
            </div>
            
            <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 8px; font-size: 12px; color: #6c757d;">
              <p style="margin: 0;">This email was sent via our lead generation system.</p>
              <p style="margin: 5px 0 0 0;">If you'd like to unsubscribe, please reply with "UNSUBSCRIBE" in the subject line.</p>
            </div>
          </div>
        `,
        text: emailBody
      })

      if (emailResult.error) {
        console.error('Resend error:', emailResult.error)
        return NextResponse.json(
          { status: 'error', message: 'Failed to send email' },
          { status: 500 }
        )
      }

      // Log email event
      const emailEventData = {
        id: randomUUID(),
        leadId: leadId || null,
        emailId: emailResult.data?.id || null,
        eventType: 'sent',
        recipientEmail: to,
        subject: subject,
        timestamp: new Date().toISOString(),
        metadata: {
          leadData: leadData || null,
          resendId: emailResult.data?.id
        }
      }

      const { error: eventError } = await supabase
        .from('email_events')
        .insert(emailEventData)

      if (eventError) {
        console.error('Error logging email event:', eventError)
        // Don't fail the request if event logging fails
      }

      // Update lead email status if leadId provided
      if (leadId) {
        const { error: updateError } = await supabase
          .from('leads')
          .update({
            emailStatus: 'sent',
            lastEmailSent: new Date().toISOString(),
            updatedAt: new Date().toISOString()
          })
          .eq('id', leadId)

        if (updateError) {
          console.error('Error updating lead email status:', updateError)
          // Don't fail the request if lead update fails
        }
      }

      // Save email draft/template for future reference
      const draftData = {
        id: randomUUID(),
        leadId: leadId || null,
        subject: subject,
        body: emailBody,
        status: 'sent',
        sentAt: new Date().toISOString(),
        createdAt: new Date().toISOString(),
        metadata: {
          recipientEmail: to,
          resendId: emailResult.data?.id,
          leadData: leadData || null
        }
      }

      const { error: draftError } = await supabase
        .from('email_drafts')
        .insert(draftData)

      if (draftError) {
        console.error('Error saving email draft:', draftError)
        // Don't fail the request if draft saving fails
      }

      return NextResponse.json({
        status: 'success',
        message: 'Email sent successfully',
        emailId: emailResult.data?.id,
        eventId: emailEventData.id
      })

    } catch (emailError) {
      console.error('Email sending error:', emailError)
      return NextResponse.json(
        { status: 'error', message: 'Failed to send email' },
        { status: 500 }
      )
    }

  } catch (error) {
    console.error('Email send API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}

// GET endpoint for email sending status or templates
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const action = searchParams.get('action')
    const leadId = searchParams.get('leadId')

    if (action === 'status' && leadId) {
      // Get email status for a specific lead
      const { data: lead, error } = await supabase
        .from('leads')
        .select('emailStatus, lastEmailSent')
        .eq('id', leadId)
        .single()

      if (error) {
        return NextResponse.json(
          { status: 'error', message: 'Lead not found' },
          { status: 404 }
        )
      }

      return NextResponse.json({
        status: 'success',
        emailStatus: lead.emailStatus || 'not_sent',
        lastEmailSent: lead.lastEmailSent
      })
    }

    if (action === 'history' && leadId) {
      // Get email history for a specific lead
      const { data: events, error } = await supabase
        .from('email_events')
        .select('*')
        .eq('leadId', leadId)
        .order('timestamp', { ascending: false })

      if (error) {
        console.error('Error fetching email history:', error)
        return NextResponse.json(
          { status: 'error', message: 'Failed to fetch email history' },
          { status: 500 }
        )
      }

      return NextResponse.json({
        status: 'success',
        events: events || []
      })
    }

    if (action === 'config') {
      // Return email configuration status
      return NextResponse.json({
        status: 'success',
        config: {
          resendConfigured: !!process.env.RESEND_API_KEY,
          fromEmail: process.env.FROM_EMAIL || 'noreply@yourdomain.com',
          maxDailyEmails: parseInt(process.env.MAX_DAILY_EMAILS || '100'),
          emailTrackingEnabled: true
        }
      })
    }

    return NextResponse.json(
      { status: 'error', message: 'Invalid action specified' },
      { status: 400 }
    )

  } catch (error) {
    console.error('Email send GET API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}