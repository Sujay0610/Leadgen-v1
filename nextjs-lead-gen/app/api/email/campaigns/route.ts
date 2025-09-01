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
    const status = searchParams.get('status')
    const limit = parseInt(searchParams.get('limit') || '50')

    let query = supabase
      .from('email_campaigns')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(limit)

    if (status) {
      query = query.eq('status', status)
    }

    const { data: campaigns, error } = await query

    if (error) {
      console.error('Error fetching campaigns:', error)
      return NextResponse.json(
        { status: 'error', message: 'Failed to fetch campaigns' },
        { status: 500 }
      )
    }

    // Enrich campaigns with metrics
    const enrichedCampaigns = await Promise.all(
      (campaigns || []).map(async (campaign) => {
        const metrics = await getCampaignMetrics(campaign.id)
        return {
          ...campaign,
          ...metrics
        }
      })
    )

    return NextResponse.json({
      status: 'success',
      campaigns: enrichedCampaigns
    })

  } catch (error) {
    console.error('Campaigns GET API error:', error)
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
      const { name, description, templateId, leadIds, scheduledAt } = body

      if (!name || !templateId || !leadIds || !Array.isArray(leadIds)) {
        return NextResponse.json(
          { status: 'error', message: 'Name, template ID, and lead IDs are required' },
          { status: 400 }
        )
      }

      const campaignData = {
        id: randomUUID(),
        name,
        description: description || '',
        templateId,
        leadIds,
        totalLeads: leadIds.length,
        sentCount: 0,
        openCount: 0,
        clickCount: 0,
        replyCount: 0,
        status: scheduledAt ? 'scheduled' : 'draft',
        scheduledAt: scheduledAt || null,
        createdAt: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }

      const { error } = await supabase
        .from('email_campaigns')
        .insert(campaignData)

      if (error) {
        console.error('Error creating campaign:', error)
        return NextResponse.json(
          { status: 'error', message: 'Failed to create campaign' },
          { status: 500 }
        )
      }

      return NextResponse.json({
        status: 'success',
        message: 'Campaign created successfully',
        campaignId: campaignData.id
      })
    }

    if (action === 'start') {
      const { campaignId } = body

      if (!campaignId) {
        return NextResponse.json(
          { status: 'error', message: 'Campaign ID is required' },
          { status: 400 }
        )
      }

      // Get campaign details
      const { data: campaign, error: campaignError } = await supabase
        .from('email_campaigns')
        .select('*')
        .eq('id', campaignId)
        .single()

      if (campaignError || !campaign) {
        return NextResponse.json(
          { status: 'error', message: 'Campaign not found' },
          { status: 404 }
        )
      }

      // Update campaign status
      const { error: updateError } = await supabase
        .from('email_campaigns')
        .update({
          status: 'active',
          startedAt: new Date().toISOString(),
          updated_at: new Date().toISOString()
        })
        .eq('id', campaignId)

      if (updateError) {
        console.error('Error starting campaign:', updateError)
        return NextResponse.json(
          { status: 'error', message: 'Failed to start campaign' },
          { status: 500 }
        )
      }

      return NextResponse.json({
        status: 'success',
        message: 'Campaign started successfully'
      })
    }

    if (action === 'pause') {
      const { campaignId } = body

      if (!campaignId) {
        return NextResponse.json(
          { status: 'error', message: 'Campaign ID is required' },
          { status: 400 }
        )
      }

      const { error } = await supabase
        .from('email_campaigns')
        .update({
          status: 'paused',
          updated_at: new Date().toISOString()
        })
        .eq('id', campaignId)

      if (error) {
        console.error('Error pausing campaign:', error)
        return NextResponse.json(
          { status: 'error', message: 'Failed to pause campaign' },
          { status: 500 }
        )
      }

      return NextResponse.json({
        status: 'success',
        message: 'Campaign paused successfully'
      })
    }

    if (action === 'stop') {
      const { campaignId } = body

      if (!campaignId) {
        return NextResponse.json(
          { status: 'error', message: 'Campaign ID is required' },
          { status: 400 }
        )
      }

      const { error } = await supabase
        .from('email_campaigns')
        .update({
          status: 'completed',
          completedAt: new Date().toISOString(),
          updated_at: new Date().toISOString()
        })
        .eq('id', campaignId)

      if (error) {
        console.error('Error stopping campaign:', error)
        return NextResponse.json(
          { status: 'error', message: 'Failed to stop campaign' },
          { status: 500 }
        )
      }

      return NextResponse.json({
        status: 'success',
        message: 'Campaign stopped successfully'
      })
    }

    return NextResponse.json(
      { status: 'error', message: 'Invalid action specified' },
      { status: 400 }
    )

  } catch (error) {
    console.error('Campaigns POST API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json()
    const { id, name, description, templateId, leadIds, scheduledAt } = body

    if (!id) {
      return NextResponse.json(
        { status: 'error', message: 'Campaign ID is required' },
        { status: 400 }
      )
    }

    const updateData: any = {
        updated_at: new Date().toISOString()
    }

    if (name) updateData.name = name
    if (description !== undefined) updateData.description = description
    if (templateId) updateData.templateId = templateId
    if (leadIds && Array.isArray(leadIds)) {
      updateData.leadIds = leadIds
      updateData.totalLeads = leadIds.length
    }
    if (scheduledAt !== undefined) updateData.scheduledAt = scheduledAt

    const { data, error } = await supabase
      .from('email_campaigns')
      .update(updateData)
      .eq('id', id)
      .select()
      .single()

    if (error) {
      console.error('Error updating campaign:', error)
      return NextResponse.json(
        { status: 'error', message: 'Failed to update campaign' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      status: 'success',
      message: 'Campaign updated successfully',
      campaign: data
    })

  } catch (error) {
    console.error('Campaigns PUT API error:', error)
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
        { status: 'error', message: 'Campaign ID is required' },
        { status: 400 }
      )
    }

    const { error } = await supabase
      .from('email_campaigns')
      .delete()
      .eq('id', id)

    if (error) {
      console.error('Error deleting campaign:', error)
      return NextResponse.json(
        { status: 'error', message: 'Failed to delete campaign' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      status: 'success',
      message: 'Campaign deleted successfully'
    })

  } catch (error) {
    console.error('Campaigns DELETE API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}

// Helper function to get campaign metrics
async function getCampaignMetrics(campaignId: string) {
  try {
    // Get email events for this campaign
    const { data: events, error } = await supabase
      .from('email_events')
      .select('eventType, created_at')
      .eq('campaignId', campaignId)

    if (error) {
      console.error('Error fetching campaign metrics:', error)
      return {
        sentCount: 0,
        openCount: 0,
        clickCount: 0,
        replyCount: 0,
        openRate: 0,
        clickRate: 0,
        replyRate: 0
      }
    }

    const sentCount = events?.filter(e => e.eventType === 'sent').length || 0
    const openCount = events?.filter(e => e.eventType === 'opened').length || 0
    const clickCount = events?.filter(e => e.eventType === 'clicked').length || 0
    const replyCount = events?.filter(e => e.eventType === 'replied').length || 0

    const openRate = sentCount > 0 ? (openCount / sentCount) * 100 : 0
    const clickRate = sentCount > 0 ? (clickCount / sentCount) * 100 : 0
    const replyRate = sentCount > 0 ? (replyCount / sentCount) * 100 : 0

    return {
      sentCount,
      openCount,
      clickCount,
      replyCount,
      openRate: Math.round(openRate * 100) / 100,
      clickRate: Math.round(clickRate * 100) / 100,
      replyRate: Math.round(replyRate * 100) / 100
    }
  } catch (error) {
    console.error('Error calculating campaign metrics:', error)
    return {
      sentCount: 0,
      openCount: 0,
      clickCount: 0,
      replyCount: 0,
      openRate: 0,
      clickRate: 0,
      replyRate: 0
    }
  }
}