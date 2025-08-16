import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

function getScoreGrade(score: number): string {
  if (score >= 95) return 'A+'
  if (score >= 90) return 'A'
  if (score >= 85) return 'B+'
  if (score >= 80) return 'B'
  if (score >= 75) return 'C+'
  if (score >= 70) return 'C'
  return 'D'
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const timeRange = searchParams.get('timeRange') || '30d'

    // Calculate date range
    const now = new Date()
    let startDate: Date
    
    switch (timeRange) {
      case '7d':
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
        break
      case '30d':
        startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
        break
      case '90d':
        startDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000)
        break
      default:
        startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
    }

    // Fetch all leads
    const { data: allLeads, error: allLeadsError } = await supabase
      .from('leads')
      .select('*')

    if (allLeadsError) {
      console.error('Error fetching all leads:', allLeadsError)
      return NextResponse.json(
        { status: 'error', message: 'Failed to fetch leads data' },
        { status: 500 }
      )
    }

    // Fetch recent leads (within time range)
    const { data: recentLeads, error: recentLeadsError } = await supabase
      .from('leads')
      .select('*')
      .gte('created_at', startDate.toISOString())

    if (recentLeadsError) {
      console.error('Error fetching recent leads:', recentLeadsError)
      return NextResponse.json(
        { status: 'error', message: 'Failed to fetch recent leads data' },
        { status: 500 }
      )
    }

    // Calculate metrics
    const totalLeads = allLeads?.length || 0
    const recentLeadsCount = recentLeads?.length || 0
    
    // Count leads with emails
    const leadsWithEmails = allLeads?.filter(lead => lead.email && lead.email.trim() !== '').length || 0
    
    // Calculate average ICP score
    const validScores = allLeads?.filter(lead => lead.icp_score && lead.icp_score > 0).map(lead => lead.icp_score) || []
    const averageIcpScore = validScores.length > 0 
      ? validScores.reduce((sum, score) => sum + score, 0) / validScores.length 
      : 0

    // Count emails sent
    const emailsSent = allLeads?.filter(lead => lead.email_status === 'sent').length || 0
    
    // Grade distribution
    const gradeDistribution = {
      'A+': 0,
      'A': 0,
      'B+': 0,
      'B': 0,
      'C+': 0,
      'C': 0,
      'D': 0
    }

    allLeads?.forEach(lead => {
      if (lead.icp_score && lead.icp_score > 0) {
        const grade = getScoreGrade(lead.icp_score)
        gradeDistribution[grade as keyof typeof gradeDistribution]++
      } else {
        gradeDistribution['D']++
      }
    })

    // Industry breakdown
    const industryBreakdown: { [key: string]: number } = {}
    allLeads?.forEach(lead => {
      if (lead.industry) {
        industryBreakdown[lead.industry] = (industryBreakdown[lead.industry] || 0) + 1
      }
    })

    // Job title breakdown
    const jobTitleBreakdown: { [key: string]: number } = {}
    allLeads?.forEach(lead => {
      if (lead.job_title) {
        jobTitleBreakdown[lead.job_title] = (jobTitleBreakdown[lead.job_title] || 0) + 1
      }
    })

    // Location breakdown
    const locationBreakdown: { [key: string]: number } = {}
    allLeads?.forEach(lead => {
      if (lead.location) {
        locationBreakdown[lead.location] = (locationBreakdown[lead.location] || 0) + 1
      }
    })

    // Email status breakdown
    const emailStatusBreakdown = {
      not_sent: allLeads?.filter(lead => lead.email_status === 'not_sent' || !lead.email_status).length || 0,
      sent: allLeads?.filter(lead => lead.email_status === 'sent').length || 0,
      opened: allLeads?.filter(lead => lead.email_status === 'opened').length || 0,
      replied: allLeads?.filter(lead => lead.email_status === 'replied').length || 0,
      bounced: allLeads?.filter(lead => lead.email_status === 'bounced').length || 0
    }

    // Source breakdown
    const sourceBreakdown: { [key: string]: number } = {}
    allLeads?.forEach(lead => {
      if (lead.source) {
        sourceBreakdown[lead.source] = (sourceBreakdown[lead.source] || 0) + 1
      }
    })

    // Daily stats for the time range
    const dailyStats: { [key: string]: { leads: number, emails: number } } = {}
    recentLeads?.forEach(lead => {
      const date = new Date(lead.created_at).toISOString().split('T')[0]
      if (!dailyStats[date]) {
        dailyStats[date] = { leads: 0, emails: 0 }
      }
      dailyStats[date].leads++
      if (lead.email && lead.email.trim() !== '') {
        dailyStats[date].emails++
      }
    })

    // Convert daily stats to array format
    const dailyStatsArray = Object.entries(dailyStats)
      .map(([date, stats]) => ({
        date,
        leads: stats.leads,
        emails: stats.emails
      }))
      .sort((a, b) => a.date.localeCompare(b.date))

    // Top companies by lead count
    const companyBreakdown: { [key: string]: number } = {}
    allLeads?.forEach(lead => {
      if (lead.company_name) {
        companyBreakdown[lead.company_name] = (companyBreakdown[lead.company_name] || 0) + 1
      }
    })

    const topCompanies = Object.entries(companyBreakdown)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10)
      .map(([company, count]) => ({ company, count }))

    // High-quality leads (A+ and A grades)
    const highQualityLeads = allLeads?.filter(lead => {
      const grade = lead.icp_score ? getScoreGrade(lead.icp_score) : 'D'
      return grade === 'A+' || grade === 'A'
    }).length || 0

    return NextResponse.json({
      status: 'success',
      metrics: {
        totalLeads,
        recentLeads: recentLeadsCount,
        leadsWithEmails,
        emailsSent,
        averageIcpScore: Math.round(averageIcpScore * 10) / 10,
        highQualityLeads,
        emailAvailabilityRate: totalLeads > 0 ? Math.round((leadsWithEmails / totalLeads) * 100) : 0,
        emailSentRate: totalLeads > 0 ? Math.round((emailsSent / totalLeads) * 100) : 0
      },
      breakdowns: {
        grades: gradeDistribution,
        industries: Object.entries(industryBreakdown)
          .sort(([, a], [, b]) => b - a)
          .slice(0, 10)
          .reduce((obj, [key, value]) => ({ ...obj, [key]: value }), {}),
        jobTitles: Object.entries(jobTitleBreakdown)
          .sort(([, a], [, b]) => b - a)
          .slice(0, 10)
          .reduce((obj, [key, value]) => ({ ...obj, [key]: value }), {}),
        locations: Object.entries(locationBreakdown)
          .sort(([, a], [, b]) => b - a)
          .slice(0, 10)
          .reduce((obj, [key, value]) => ({ ...obj, [key]: value }), {}),
        emailStatus: emailStatusBreakdown,
        sources: sourceBreakdown,
        topCompanies
      },
      trends: {
        dailyStats: dailyStatsArray,
        timeRange
      }
    })

  } catch (error) {
    console.error('Metrics API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}