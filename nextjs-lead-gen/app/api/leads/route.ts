import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const page = parseInt(searchParams.get('page') || '1')
    const limit = parseInt(searchParams.get('limit') || '50')
    const search = searchParams.get('search') || ''
    const minScore = parseFloat(searchParams.get('minScore') || '0')
    const maxScore = parseFloat(searchParams.get('maxScore') || '100')
    const company = searchParams.get('company') || ''
    const jobTitle = searchParams.get('jobTitle') || ''
    const emailStatus = searchParams.get('emailStatus') || ''
    const sortBy = searchParams.get('sortBy') || 'created_at'
    const sortOrder = searchParams.get('sortOrder') || 'desc'

    // Build query
    let query = supabase
      .from('leads')
      .select('*', { count: 'exact' })

    // Apply filters
    if (search) {
      query = query.or(`full_name.ilike.%${search}%,company_name.ilike.%${search}%,job_title.ilike.%${search}%,email.ilike.%${search}%`)
    }

    if (minScore > 0 || maxScore < 100) {
      query = query.gte('icp_score', minScore).lte('icp_score', maxScore)
    }

    if (company) {
      query = query.ilike('company_name', `%${company}%`)
    }

    if (jobTitle) {
      query = query.ilike('job_title', `%${jobTitle}%`)
    }

    if (emailStatus) {
      query = query.eq('email_status', emailStatus)
    }

    // Apply sorting
    query = query.order(sortBy, { ascending: sortOrder === 'asc' })

    // Apply pagination
    const offset = (page - 1) * limit
    query = query.range(offset, offset + limit - 1)

    const { data: leads, error, count } = await query

    if (error) {
      console.error('Error fetching leads:', error)
      return NextResponse.json(
        { status: 'error', message: 'Failed to fetch leads' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      status: 'success',
      leads: leads || [],
      pagination: {
        page,
        limit,
        total: count || 0,
        totalPages: Math.ceil((count || 0) / limit)
      }
    })

  } catch (error) {
    console.error('Leads API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { action, leadId, leadData } = body

    if (action === 'update') {
      if (!leadId || !leadData) {
        return NextResponse.json(
          { status: 'error', message: 'Lead ID and data are required for update' },
          { status: 400 }
        )
      }

      const { error } = await supabase
        .from('leads')
        .update({
          ...leadData,
          updated_at: new Date().toISOString()
        })
        .eq('id', leadId)

      if (error) {
        console.error('Error updating lead:', error)
        return NextResponse.json(
          { status: 'error', message: 'Failed to update lead' },
          { status: 500 }
        )
      }

      return NextResponse.json({
        status: 'success',
        message: 'Lead updated successfully'
      })
    }

    if (action === 'delete') {
      if (!leadId) {
        return NextResponse.json(
          { status: 'error', message: 'Lead ID is required for deletion' },
          { status: 400 }
        )
      }

      const { error } = await supabase
        .from('leads')
        .delete()
        .eq('id', leadId)

      if (error) {
        console.error('Error deleting lead:', error)
        return NextResponse.json(
          { status: 'error', message: 'Failed to delete lead' },
          { status: 500 }
        )
      }

      return NextResponse.json({
        status: 'success',
        message: 'Lead deleted successfully'
      })
    }

    if (action === 'bulk_update') {
      const { leadIds, updates } = body

      if (!leadIds || !Array.isArray(leadIds) || leadIds.length === 0) {
        return NextResponse.json(
          { status: 'error', message: 'Lead IDs array is required for bulk update' },
          { status: 400 }
        )
      }

      const { error } = await supabase
        .from('leads')
        .update({
          ...updates,
          updated_at: new Date().toISOString()
        })
        .in('id', leadIds)

      if (error) {
        console.error('Error bulk updating leads:', error)
        return NextResponse.json(
          { status: 'error', message: 'Failed to bulk update leads' },
          { status: 500 }
        )
      }

      return NextResponse.json({
        status: 'success',
        message: `Updated ${leadIds.length} leads successfully`
      })
    }

    if (action === 'bulk_delete') {
      const { leadIds } = body

      if (!leadIds || !Array.isArray(leadIds) || leadIds.length === 0) {
        return NextResponse.json(
          { status: 'error', message: 'Lead IDs array is required for bulk delete' },
          { status: 400 }
        )
      }

      const { error } = await supabase
        .from('leads')
        .delete()
        .in('id', leadIds)

      if (error) {
        console.error('Error bulk deleting leads:', error)
        return NextResponse.json(
          { status: 'error', message: 'Failed to bulk delete leads' },
          { status: 500 }
        )
      }

      return NextResponse.json({
        status: 'success',
        message: `Deleted ${leadIds.length} leads successfully`
      })
    }

    return NextResponse.json(
      { status: 'error', message: 'Invalid action specified' },
      { status: 400 }
    )

  } catch (error) {
    console.error('Leads POST API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json()
    const { id, ...updateData } = body

    if (!id) {
      return NextResponse.json(
        { status: 'error', message: 'Lead ID is required' },
        { status: 400 }
      )
    }

    const { data, error } = await supabase
      .from('leads')
      .update({
        ...updateData,
        updatedAt: new Date().toISOString()
      })
      .eq('id', id)
      .select()
      .single()

    if (error) {
      console.error('Error updating lead:', error)
      return NextResponse.json(
        { status: 'error', message: 'Failed to update lead' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      status: 'success',
      message: 'Lead updated successfully',
      lead: data
    })

  } catch (error) {
    console.error('Leads PUT API error:', error)
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
        { status: 'error', message: 'Lead ID is required' },
        { status: 400 }
      )
    }

    const { error } = await supabase
      .from('leads')
      .delete()
      .eq('id', id)

    if (error) {
      console.error('Error deleting lead:', error)
      return NextResponse.json(
        { status: 'error', message: 'Failed to delete lead' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      status: 'success',
      message: 'Lead deleted successfully'
    })

  } catch (error) {
    console.error('Leads DELETE API error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}