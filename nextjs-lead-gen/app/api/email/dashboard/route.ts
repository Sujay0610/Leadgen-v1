import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const timeRange = searchParams.get('timeRange') || '30' // days
    const days = parseInt(timeRange)

    const startDate = new Date()
    startDate.setDate(startDate.getDate() - days)
    const startDateStr = startDate.toISOString()

    // Get email events for the time range
    const { data: events, error: eventsError } = await supabase
      .from('email_events')
      .select('*')
      .gte('created_at', startDateStr)
      .order('created_at', { ascending: false })

    // Get leads data separately to avoid foreign key issues
let leadsData: { id: string; firstName: string; lastName: string; fullName: string; email: string; jobTitle: string; companyName: string; }[] = [];
    if (events && events.length > 0) {
      const leadIds = [...new Set(events.filter(e => e.leadId).map(e => e.leadId))]
      if (leadIds.length > 0) {
        const { data: leads } = await supabase
          .from('leads')
          .select('id, firstName, lastName, fullName, email, jobTitle, companyName')
          .in('id', leadIds)
        leadsData = leads || []
      }
    }

    // Merge events with lead data
    const eventsWithLeads = events ? events.map(event => {
      const lead = leadsData.find(l => l.id === event.leadId)
      return {
        ...event,
        leads: lead || null
      }
    }) : []

    if (eventsError) {
      console.error('Error fetching email events:', eventsError)
      return NextResponse.json(
        { status: 'error', message: 'Failed to fetch email events' },
        { status: 500 }
      )
    }

    // Get campaigns for the time range
    const { data: campaigns, error: campaignsError } = await supabase
      .from('email_campaigns')
      .select('*')
      .gte('created_at', startDateStr)
      .order('created_at', { ascending: false })

    if (campaignsError) {
      console.error('Error fetching campaigns:', campaignsError)
      return NextResponse.json(
        { status: 'error', message: 'Failed to fetch campaigns' },
        { status: 500 }
      )
    }

    // Calculate overall metrics
    const totalSent = eventsWithLeads?.filter(e => e.eventType === 'sent').length || 0
    const totalOpened = eventsWithLeads?.filter(e => e.eventType === 'opened').length || 0
    const totalClicked = eventsWithLeads?.filter(e => e.eventType === 'clicked').length || 0
    const totalReplied = eventsWithLeads?.filter(e => e.eventType === 'replied').length || 0

    const openRate = totalSent > 0 ? (totalOpened / totalSent) * 100 : 0
    const clickRate = totalSent > 0 ? (totalClicked / totalSent) * 100 : 0
    const replyRate = totalSent > 0 ? (totalReplied / totalSent) * 100 : 0

    // Calculate daily metrics for charts
    const dailyMetrics = calculateDailyMetrics(eventsWithLeads || [], days)

    // Calculate engagement breakdown for pie chart
    const engagementBreakdown = [
      { name: 'Opened', value: totalOpened, color: '#10B981' },
      { name: 'Clicked', value: totalClicked, color: '#3B82F6' },
      { name: 'Replied', value: totalReplied, color: '#8B5CF6' },
      { name: 'No Response', value: Math.max(0, totalSent - totalOpened), color: '#6B7280' }
    ]

    // Calculate campaign performance
    const campaignPerformance = await Promise.all(
      (campaigns || []).map(async (campaign) => {
        const campaignEvents = eventsWithLeads?.filter(e => e.campaignId === campaign.id) || []
        const sent = campaignEvents.filter(e => e.eventType === 'sent').length
        const opened = campaignEvents.filter(e => e.eventType === 'opened').length
        const clicked = campaignEvents.filter(e => e.eventType === 'clicked').length
        const replied = campaignEvents.filter(e => e.eventType === 'replied').length

        return {
          id: campaign.id,
          name: campaign.name,
          status: campaign.status,
          totalLeads: campaign.totalLeads || 0,
          sent,
          opened,
          clicked,
          replied,
          openRate: sent > 0 ? Math.round((opened / sent) * 100 * 100) / 100 : 0,
          clickRate: sent > 0 ? Math.round((clicked / sent) * 100 * 100) / 100 : 0,
          replyRate: sent > 0 ? Math.round((replied / sent) * 100 * 100) / 100 : 0,
          createdAt: campaign.created_at
        }
      })
    )

    // Get recent activity (last 20 events)
    const recentActivity = (eventsWithLeads || [])
      .slice(0, 20)
      .map(event => ({
        id: event.id,
        type: event.eventType,
        leadName: event.leads?.fullName || `${event.leads?.firstName || ''} ${event.leads?.lastName || ''}`.trim(),
        leadEmail: event.leads?.email,
        leadCompany: event.leads?.companyName,
        timestamp: event.created_at,
        campaignId: event.campaignId
      }))

    const metrics = {
      totalSent,
      openRate: Math.round(openRate * 100) / 100,
      clickRate: Math.round(clickRate * 100) / 100,
      replyRate: Math.round(replyRate * 100) / 100
    }

    return NextResponse.json({
      status: 'success',
      data: {
        metrics,
        dailyMetrics,
        engagementBreakdown,
        campaignPerformance,
        recentActivity,
        timeRange: days
      }
    })

  } catch (error) {
    console.error('Email dashboard API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}

function calculateDailyMetrics(events: any[], days: number) {
  const dailyData: { [key: string]: { sent: number; opened: number; clicked: number; replied: number } } = {}

  // Initialize all days with zero values
  for (let i = 0; i < days; i++) {
    const date = new Date()
    date.setDate(date.getDate() - i)
    const dateStr = date.toISOString().split('T')[0]
    dailyData[dateStr] = { sent: 0, opened: 0, clicked: 0, replied: 0 }
  }

  // Count events by day
  events.forEach(event => {
    const eventDate = new Date(event.created_at).toISOString().split('T')[0]
    if (dailyData[eventDate]) {
      switch (event.eventType) {
        case 'sent':
          dailyData[eventDate].sent++
          break
        case 'opened':
          dailyData[eventDate].opened++
          break
        case 'clicked':
          dailyData[eventDate].clicked++
          break
        case 'replied':
          dailyData[eventDate].replied++
          break
      }
    }
  })

  // Convert to array format for charts
  return Object.entries(dailyData)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, data]) => ({
      date,
      sent: data.sent,
      opened: data.opened,
      clicked: data.clicked,
      replied: data.replied,
      openRate: data.sent > 0 ? Math.round((data.opened / data.sent) * 100 * 100) / 100 : 0
    }))
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { action } = body

    if (action === 'refresh') {
      // This endpoint can be used to trigger data refresh
      // For now, we'll just return success as the GET endpoint always fetches fresh data
      return NextResponse.json({
        status: 'success',
        message: 'Dashboard data refreshed'
      })
    }

    if (action === 'export') {
      const { timeRange, format } = body
      
      // This could be extended to export dashboard data in different formats
      // For now, we'll return the same data as GET endpoint
      const dashboardData = await fetch(`${request.url}?timeRange=${timeRange || '30'}`, {
        method: 'GET'
      })
      
      const data = await dashboardData.json()
      
      return NextResponse.json({
        status: 'success',
        message: 'Dashboard data exported',
        data: data.data,
        format: format || 'json'
      })
    }

    return NextResponse.json(
      { status: 'error', message: 'Invalid action specified' },
      { status: 400 }
    )

  } catch (error) {
    console.error('Email dashboard POST API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}