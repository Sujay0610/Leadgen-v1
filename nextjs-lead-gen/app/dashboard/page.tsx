'use client'

import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts'
import { Mail, TrendingUp, Users, Calendar, Eye, Reply, MousePointer, RefreshCw } from 'lucide-react'
import { toast } from 'react-hot-toast'
import apiClient from '@/lib/api-client'

interface EmailMetrics {
  totalSent: number
  totalOpened: number
  totalClicked: number
  totalReplied: number
  openRate: number
  clickRate: number
  replyRate: number
  bounceRate: number
}

interface DailyStats {
  date: string
  sent: number
  opened: number
  clicked: number
  replied: number
}

interface CampaignPerformance {
  id: string
  name: string
  sent: number
  opened: number
  clicked: number
  replied: number
  openRate: number
  clickRate: number
  replyRate: number
}

interface EmailEvent {
  id: string
  type: 'sent' | 'opened' | 'clicked' | 'replied' | 'bounced'
  leadName: string
  companyName: string
  subject: string
  timestamp: string
}

export default function EmailDashboard() {
  const [metrics, setMetrics] = useState<EmailMetrics | null>(null)
  const [dailyStats, setDailyStats] = useState<DailyStats[]>([])
  const [campaigns, setCampaigns] = useState<CampaignPerformance[]>([])
  const [recentEvents, setRecentEvents] = useState<EmailEvent[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [timeRange, setTimeRange] = useState('7d')

  useEffect(() => {
    fetchDashboardData()
  }, [timeRange])

  const fetchDashboardData = async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.getEmailDashboard(timeRange)
      const data = response.data

      if (data.status === 'success') {
        setMetrics(data.data.metrics)
        setDailyStats(data.data.dailyStats || [])
        setCampaigns(data.data.campaigns || [])
        setRecentEvents(data.data.recentEvents || [])
      } else {
        toast.error(data.message || 'Failed to fetch dashboard data')
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
      toast.error('Error loading dashboard data')
    } finally {
      setIsLoading(false)
    }
  }

  const pieData = metrics ? [
    { name: 'Opened', value: metrics.totalOpened, color: '#10B981' },
    { name: 'Clicked', value: metrics.totalClicked, color: '#3B82F6' },
    { name: 'Replied', value: metrics.totalReplied, color: '#8B5CF6' },
    { name: 'No Action', value: metrics.totalSent - metrics.totalOpened, color: '#6B7280' }
  ] : []

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'sent': return <Mail className="h-4 w-4 text-blue-500" />
      case 'opened': return <Eye className="h-4 w-4 text-green-500" />
      case 'clicked': return <MousePointer className="h-4 w-4 text-purple-500" />
      case 'replied': return <Reply className="h-4 w-4 text-orange-500" />
      case 'bounced': return <TrendingUp className="h-4 w-4 text-red-500" />
      default: return <Mail className="h-4 w-4 text-gray-500" />
    }
  }

  const getEventColor = (type: string) => {
    switch (type) {
      case 'sent': return 'bg-blue-50 border-blue-200'
      case 'opened': return 'bg-green-50 border-green-200'
      case 'clicked': return 'bg-purple-50 border-purple-200'
      case 'replied': return 'bg-orange-50 border-orange-200'
      case 'bounced': return 'bg-red-50 border-red-200'
      default: return 'bg-gray-50 border-gray-200'
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              📊 Email Dashboard
            </h1>
            <p className="text-gray-600">
              Track email performance and engagement metrics
            </p>
          </div>
          <div className="flex items-center gap-4">
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="input-field w-32"
            >
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
            </select>
            <button
              onClick={fetchDashboardData}
              className="btn-secondary flex items-center gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
          </div>
        </div>

        {/* Metrics Cards */}
        {metrics && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Sent</p>
                  <p className="text-2xl font-bold text-gray-900">{metrics.totalSent.toLocaleString()}</p>
                </div>
                <Mail className="h-8 w-8 text-blue-500" />
              </div>
            </div>

            <div className="card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Open Rate</p>
                  <p className="text-2xl font-bold text-gray-900">{metrics.openRate.toFixed(1)}%</p>
                  <p className="text-sm text-gray-500">{metrics.totalOpened} opened</p>
                </div>
                <Eye className="h-8 w-8 text-green-500" />
              </div>
            </div>

            <div className="card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Click Rate</p>
                  <p className="text-2xl font-bold text-gray-900">{metrics.clickRate.toFixed(1)}%</p>
                  <p className="text-sm text-gray-500">{metrics.totalClicked} clicked</p>
                </div>
                <MousePointer className="h-8 w-8 text-purple-500" />
              </div>
            </div>

            <div className="card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Reply Rate</p>
                  <p className="text-2xl font-bold text-gray-900">{metrics.replyRate.toFixed(1)}%</p>
                  <p className="text-sm text-gray-500">{metrics.totalReplied} replied</p>
                </div>
                <Reply className="h-8 w-8 text-orange-500" />
              </div>
            </div>
          </div>
        )}

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Daily Performance Chart */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">📈 Daily Performance</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={dailyStats}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="sent" stroke="#3B82F6" name="Sent" />
                <Line type="monotone" dataKey="opened" stroke="#10B981" name="Opened" />
                <Line type="monotone" dataKey="clicked" stroke="#8B5CF6" name="Clicked" />
                <Line type="monotone" dataKey="replied" stroke="#F59E0B" name="Replied" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Email Engagement Breakdown */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">🎯 Engagement Breakdown</h3>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Campaign Performance */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">🚀 Campaign Performance</h3>
            <div className="space-y-4">
              {campaigns.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No campaigns found</p>
              ) : (
                campaigns.map((campaign) => (
                  <div key={campaign.id} className="border border-gray-200 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-2">{campaign.name}</h4>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">Sent:</span>
                        <span className="ml-2 font-medium">{campaign.sent}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Open Rate:</span>
                        <span className="ml-2 font-medium">{campaign.openRate.toFixed(1)}%</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Reply Rate:</span>
                        <span className="ml-2 font-medium">{campaign.replyRate.toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Recent Activity */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">⚡ Recent Activity</h3>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {recentEvents.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No recent activity</p>
              ) : (
                recentEvents.map((event) => (
                  <div key={event.id} className={`border rounded-lg p-3 ${getEventColor(event.type)}`}>
                    <div className="flex items-start gap-3">
                      {getEventIcon(event.type)}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900">
                          {event.leadName} at {event.companyName}
                        </p>
                        <p className="text-sm text-gray-600 truncate">
                          {event.subject}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          {event.type.charAt(0).toUpperCase() + event.type.slice(1)} • {new Date(event.timestamp).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}