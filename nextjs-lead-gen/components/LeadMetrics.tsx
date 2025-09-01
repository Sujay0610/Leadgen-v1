'use client'

import { useState, useEffect } from 'react'
import { Users, Mail, TrendingUp, Target, Loader2 } from 'lucide-react'
import apiClient from '@/lib/api-client'

interface MetricData {
  totalLeads: number
  emailsAvailable: number
  averageIcpScore: number
  recentLeads: number
}

interface LeadMetricsProps {
  className?: string
  refreshTrigger?: number
}

export default function LeadMetrics({ className = '', refreshTrigger = 0 }: LeadMetricsProps) {
  const [metrics, setMetrics] = useState<MetricData>({
    totalLeads: 0,
    emailsAvailable: 0,
    averageIcpScore: 0,
    recentLeads: 0
  })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchMetrics()
  }, [refreshTrigger])

  const fetchMetrics = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      console.log('🔄 Fetching metrics...')
      
      // Use apiClient which handles authentication properly
      const response = await apiClient.getLeadMetrics('30d')
      console.log('📊 Metrics API response:', response)
      
      const data = response.data
      console.log('📊 Metrics data:', data)
      
      if (data && data.status === 'success') {
        // Support both Next.js route shape { status, metrics, breakdowns, trends }
        // and FastAPI shape { status, data: { overview, breakdown, trends } }
        let metricsData: any = null
        
        if (data.metrics) {
          metricsData = data.metrics
        } else if (data.data && data.data.overview) {
          const overview = data.data.overview
          metricsData = {
            totalLeads: overview.totalLeads ?? overview.total_leads ?? 0,
            // Use emailsAvailable from backend response
            emailsAvailable: overview.emailsAvailable ?? 0,
            // Map average score naming from backend to frontend expectation
            averageIcpScore: overview.averageScore ?? 0,
            // Map recent/new leads
            recentLeads: overview.newLeads ?? 0,
          }
        }

        if (metricsData) {
          console.log('✅ Setting metrics:', metricsData)
          setMetrics({
            totalLeads: metricsData?.totalLeads || 0,
            emailsAvailable: metricsData?.emailsAvailable ?? 0,
            averageIcpScore: metricsData?.averageIcpScore ?? metricsData?.averageScore ?? 0,
            recentLeads: metricsData?.recentLeads ?? metricsData?.newLeads ?? 0
          })
        } else {
          console.error('❌ API response error (unknown shape):', data)
          setError(data?.message || 'Failed to fetch metrics')
        }
      } else {
        console.error('❌ API response error:', data)
        setError(data?.message || 'Failed to fetch metrics')
      }
    } catch (error) {
      console.error('❌ Error fetching metrics:', error)
      console.error('❌ Error details:', {
        message: (error as any).message,
        response: (error as any).response?.data,
        status: (error as any).response?.status
      })
      setError(`Failed to fetch metrics: ${(error as any).message}`)
    } finally {
      setIsLoading(false)
    }
  }

  const formatPercentage = (value: number) => {
    return `${Math.round(value || 0)}/100`
  }

  const getScoreColor = (score: number) => {
    const safeScore = score || 0
    if (safeScore >= 80) return 'text-success-600'
    if (safeScore >= 60) return 'text-warning-600'
    return 'text-error-600'
  }

  const getScoreGrade = (score: number) => {
    const safeScore = score || 0
    if (safeScore >= 80) return 'A+'
    if (safeScore >= 70) return 'A'
    if (safeScore >= 60) return 'B'
    if (safeScore >= 50) return 'C'
    return 'D'
  }

  if (isLoading) {
    return (
      <div className={`card ${className}`}>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          <span className="ml-2 text-gray-600">Loading metrics...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`card ${className}`}>
        <div className="text-center py-8">
          <div className="text-error-600 mb-2">Failed to load metrics</div>
          <button
            onClick={fetchMetrics}
            className="btn-secondary text-sm"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Leads */}
        <div className="metric-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Leads</p>
              <p className="text-2xl font-bold text-gray-900">
                {(metrics.totalLeads || 0).toLocaleString()}
              </p>
            </div>
            <div className="p-3 bg-primary-100 rounded-full">
              <Users className="h-6 w-6 text-primary-600" />
            </div>
          </div>
        </div>

        {/* Emails Available */}
        <div className="metric-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Emails Available</p>
              <p className="text-2xl font-bold text-gray-900">
                {(metrics.emailsAvailable || 0).toLocaleString()}
              </p>
              <p className="text-xs text-gray-500">
                  {(metrics.totalLeads || 0) > 0 
                    ? `${Math.round(((metrics.emailsAvailable || 0) / (metrics.totalLeads || 1)) * 100)}% of leads`
                    : '0% of leads'
                  }
                </p>
            </div>
            <div className="p-3 bg-success-100 rounded-full">
              <Mail className="h-6 w-6 text-success-600" />
            </div>
          </div>
        </div>

        {/* Average ICP Score */}
        <div className="metric-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Avg ICP Score</p>
              <div className="flex items-baseline gap-2">
                <p className={`text-2xl font-bold ${getScoreColor(metrics.averageIcpScore)}`}>
                  {formatPercentage(metrics.averageIcpScore)}
                </p>
                <span className={`text-sm font-medium ${getScoreColor(metrics.averageIcpScore)}`}>
                  ({getScoreGrade(metrics.averageIcpScore)})
                </span>
              </div>
            </div>
            <div className="p-3 bg-warning-100 rounded-full">
              <Target className="h-6 w-6 text-warning-600" />
            </div>
          </div>
        </div>

        {/* Recent Leads */}
        <div className="metric-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Recent Leads</p>
              <p className="text-2xl font-bold text-gray-900">
                {(metrics.recentLeads || 0).toLocaleString()}
              </p>
              <p className="text-xs text-gray-500">Last 7 days</p>
            </div>
            <div className="p-3 bg-blue-100 rounded-full">
              <TrendingUp className="h-6 w-6 text-blue-600" />
            </div>
          </div>
        </div>
      </div>


    </div>
  )
}