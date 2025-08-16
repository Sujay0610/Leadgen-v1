import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { randomUUID } from 'crypto'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const leadId = searchParams.get('leadId')
    const status = searchParams.get('status')
    const limit = parseInt(searchParams.get('limit') || '50')

    let query = supabase
      .from('email_drafts')
      .select(`
        *,
        leads!inner(
          id,
          firstName,
          lastName,
          fullName,
          email,
          jobTitle,
          companyName
        )
      `)
      .order('created_at', { ascending: false })
      .limit(limit)

    if (leadId) {
      query = query.eq('leadId', leadId)
    }

    if (status) {
      query = query.eq('status', status)
    }

    const { data: drafts, error } = await query

    if (error) {
      console.error('Error fetching drafts:', error)
      return NextResponse.json(
        { status: 'error', message: 'Failed to fetch drafts' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      status: 'success',
      drafts: drafts || []
    })

  } catch (error) {
    console.error('Drafts GET API error:', error)
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

    if (action === 'create') {
      const { leadId, subject, body: emailBody, scheduledAt, campaignId } = body

      if (!leadId || !subject || !emailBody) {
        return NextResponse.json(
          { status: 'error', message: 'Lead ID, subject, and body are required' },
          { status: 400 }
        )
      }

      const draftData = {
        id: randomUUID(),
        leadId,
        subject,
        body: emailBody,
        status: scheduledAt ? 'scheduled' : 'draft',
        scheduledAt: scheduledAt || null,
        campaignId: campaignId || null,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      }

      const { error } = await supabase
        .from('email_drafts')
        .insert(draftData)

      if (error) {
        console.error('Error creating draft:', error)
        return NextResponse.json(
          { status: 'error', message: 'Failed to create draft' },
          { status: 500 }
        )
      }

      return NextResponse.json({
        status: 'success',
        message: 'Draft created successfully',
        draftId: draftData.id
      })
    }

    if (action === 'send') {
      const { draftId } = body

      if (!draftId) {
        return NextResponse.json(
          { status: 'error', message: 'Draft ID is required' },
          { status: 400 }
        )
      }

      // Get draft details with lead information
      const { data: draft, error: draftError } = await supabase
        .from('email_drafts')
        .select(`
          *,
          leads!inner(
            id,
            firstName,
            lastName,
            fullName,
            email,
            jobTitle,
            companyName
          )
        `)
        .eq('id', draftId)
        .single()

      if (draftError || !draft) {
        return NextResponse.json(
          { status: 'error', message: 'Draft not found' },
          { status: 404 }
        )
      }

      // Send email via the email/send API
      try {
        const sendResponse = await fetch(`${process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000'}/api/email/send`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            to: draft.leads.email,
            subject: draft.subject,
            body: draft.body,
            leadId: draft.leadId,
            campaignId: draft.campaignId
          })
        })

        const sendResult = await sendResponse.json()

        if (sendResult.status !== 'success') {
          return NextResponse.json(
            { status: 'error', message: sendResult.message || 'Failed to send email' },
            { status: 500 }
          )
        }

        // Update draft status to sent
        const { error: updateError } = await supabase
          .from('email_drafts')
          .update({
            status: 'sent',
            sentAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
          })
          .eq('id', draftId)

        if (updateError) {
          console.error('Error updating draft status:', updateError)
        }

        return NextResponse.json({
          status: 'success',
          message: 'Email sent successfully'
        })

      } catch (error) {
        console.error('Error sending email from draft:', error)
        return NextResponse.json(
          { status: 'error', message: 'Failed to send email' },
          { status: 500 }
        )
      }
    }

    if (action === 'schedule') {
      const { draftId, scheduledAt } = body

      if (!draftId || !scheduledAt) {
        return NextResponse.json(
          { status: 'error', message: 'Draft ID and scheduled time are required' },
          { status: 400 }
        )
      }

      const { error } = await supabase
        .from('email_drafts')
        .update({
          status: 'scheduled',
          scheduledAt,
          updatedAt: new Date().toISOString()
        })
        .eq('id', draftId)

      if (error) {
        console.error('Error scheduling draft:', error)
        return NextResponse.json(
          { status: 'error', message: 'Failed to schedule draft' },
          { status: 500 }
        )
      }

      return NextResponse.json({
        status: 'success',
        message: 'Draft scheduled successfully'
      })
    }

    if (action === 'unschedule') {
      const { draftId } = body

      if (!draftId) {
        return NextResponse.json(
          { status: 'error', message: 'Draft ID is required' },
          { status: 400 }
        )
      }

      const { error } = await supabase
        .from('email_drafts')
        .update({
          status: 'draft',
          scheduledAt: null,
          updatedAt: new Date().toISOString()
        })
        .eq('id', draftId)

      if (error) {
        console.error('Error unscheduling draft:', error)
        return NextResponse.json(
          { status: 'error', message: 'Failed to unschedule draft' },
          { status: 500 }
        )
      }

      return NextResponse.json({
        status: 'success',
        message: 'Draft unscheduled successfully'
      })
    }

    return NextResponse.json(
      { status: 'error', message: 'Invalid action specified' },
      { status: 400 }
    )

  } catch (error) {
    console.error('Drafts POST API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json()
    const { id, subject, body: emailBody, scheduledAt, campaignId } = body

    if (!id) {
      return NextResponse.json(
        { status: 'error', message: 'Draft ID is required' },
        { status: 400 }
      )
    }

    const updateData: any = {
      updatedAt: new Date().toISOString()
    }

    if (subject) updateData.subject = subject
    if (emailBody) updateData.body = emailBody
    if (scheduledAt !== undefined) {
      updateData.scheduledAt = scheduledAt
      updateData.status = scheduledAt ? 'scheduled' : 'draft'
    }
    if (campaignId !== undefined) updateData.campaignId = campaignId

    const { data, error } = await supabase
      .from('email_drafts')
      .update(updateData)
      .eq('id', id)
      .select(`
        *,
        leads!inner(
          id,
          firstName,
          lastName,
          fullName,
          email,
          jobTitle,
          companyName
        )
      `)
      .single()

    if (error) {
      console.error('Error updating draft:', error)
      return NextResponse.json(
        { status: 'error', message: 'Failed to update draft' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      status: 'success',
      message: 'Draft updated successfully',
      draft: data
    })

  } catch (error) {
    console.error('Drafts PUT API error:', error)
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
        { status: 'error', message: 'Draft ID is required' },
        { status: 400 }
      )
    }

    const { error } = await supabase
      .from('email_drafts')
      .delete()
      .eq('id', id)

    if (error) {
      console.error('Error deleting draft:', error)
      return NextResponse.json(
        { status: 'error', message: 'Failed to delete draft' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      status: 'success',
      message: 'Draft deleted successfully'
    })

  } catch (error) {
    console.error('Drafts DELETE API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}