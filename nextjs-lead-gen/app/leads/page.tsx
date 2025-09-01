'use client'

import { useState, useEffect } from 'react'
import { 
  Database, 
  Search, 
  Filter, 
  Mail, 
  ExternalLink, 
  ChevronDown,
  Loader2,
  RefreshCw
} from 'lucide-react'
import { toast } from 'react-hot-toast'
import LeadMetrics from '@/components/LeadMetrics'
import EmailModal from '@/components/EmailModal'
import ChatInterface from '@/components/ChatInterface'
import APIStatus from '@/components/APIStatus'
import apiClient from '@/lib/api-client'

interface Lead {
  id: string
  linkedin_url: string
  full_name: string
  first_name: string
  last_name: string
  headline: string
  about: string
  email: string

  email_status: 'available' | 'sent' | 'bounced' | 'not_available'
  phone_number: string
  job_title: string
  seniority: string
  departments: string
  subdepartments: string
  functions: string
  work_experience_months: number
  employment_history: string
  location: string
  city: string
  state: string
  country: string
  company_name: string
  company_website: string
  company_domain: string
  company_linkedin: string
  company_twitter: string
  company_facebook: string
  company_phone: string
  company_size: string
  company_industry: string
  company_founded_year: number
  company_growth_6month: string
  company_growth_12month: string
  company_growth_24month: string
  photo_url: string
  experience: string
  intent_strength: string
  show_intent: boolean
  email_domain_catchall: boolean
  revealed_for_current_team: boolean
  icp_score: number
  icp_percentage: number
  icp_grade: string
  icp_breakdown: string
  send_email_status: string
  scraping_status: string
  error_message: string
  scraped_at: string
  created_at: string
  updated_at: string
}

interface Filters {
  search: string
  icpScoreMin: number
  icpScoreMax: number
  emailStatus: string
  hasEmail: boolean
  location: string
  sortBy: string
  sortOrder: 'asc' | 'desc'
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [filteredLeads, setFilteredLeads] = useState<Lead[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null)
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [showChat, setShowChat] = useState(false)
  const [leadMetrics, setLeadMetrics] = useState({
    total: 0,
    withEmail: 0,
    avgIcpScore: 0,
    recentlyGenerated: 0
  })
  
  const [filters, setFilters] = useState<Filters>({
    search: '',
    icpScoreMin: 0,
    icpScoreMax: 100,
    emailStatus: '',
    hasEmail: true, // Default to checked
    location: '',
    sortBy: 'created_at',
    sortOrder: 'desc' // Recent leads first
  })

  useEffect(() => {
    fetchLeads()
  }, [])

  useEffect(() => {
    applyFilters()
  }, [leads, filters])

  const calculateMetrics = (leadsData: Lead[]) => {
    const total = leadsData.length
    const withEmail = leadsData.filter(lead => 
      (lead.email && lead.email.trim() !== '') || 
      (lead.email && lead.email.trim() !== '')
    ).length
    
    const icpScores = leadsData
      .map(lead => lead.icp_percentage || 0)
      .filter(score => score > 0)
    const avgIcpScore = icpScores.length > 0 
      ? icpScores.reduce((sum, score) => sum + score, 0) / icpScores.length 
      : 0
    
    // Count leads generated in the last 24 hours
    const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000)
    const recentlyGenerated = leadsData.filter(lead => 
      new Date(lead.created_at) > oneDayAgo
    ).length
    
    setLeadMetrics({
      total,
      withEmail,
      avgIcpScore: Math.round(avgIcpScore * 10) / 10,
      recentlyGenerated
    })
  }

  const fetchLeads = async () => {
    try {
      setIsLoading(true)
      console.log('Fetching leads with filters:', filters)
      
      const response = await apiClient.getLeads({
        page: 1,
        limit: 1000, // Get all leads for now
        search: filters.search,
        minScore: filters.icpScoreMin,
        maxScore: filters.icpScoreMax,
        emailStatus: filters.emailStatus || undefined
      })
      
      console.log('Full API response:', response)
      const data = response.data
      console.log('Response data:', data)
      
      if (data.status === 'success') {
        const leadsData = data.leads || data.data || []
        console.log('Leads data extracted:', leadsData)
        console.log('Number of leads:', leadsData.length)
        setLeads(leadsData)
        calculateMetrics(leadsData)
      } else {
        console.error('API returned error status:', data)
        toast.error(data.message || 'Failed to fetch leads')
      }
    } catch (error: any) {
      console.error('Error fetching leads:', error)
      console.error('Error response:', error.response)
      const errorMessage = error.response?.data?.message || error.message || 'Failed to fetch leads'
      toast.error(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const applyFilters = () => {
    let filtered = leads.filter(lead => {
      const matchesSearch = !filters.search || 
        lead.full_name?.toLowerCase().includes(filters.search.toLowerCase()) ||
        lead.company_name?.toLowerCase().includes(filters.search.toLowerCase()) ||
        lead.job_title?.toLowerCase().includes(filters.search.toLowerCase())
      
      const matchesICPScore = (lead.icp_percentage || 0) >= filters.icpScoreMin && 
        (lead.icp_percentage || 0) <= filters.icpScoreMax
      
      const matchesEmailStatus = !filters.emailStatus || 
        lead.email_status === filters.emailStatus
      
      const matchesHasEmail = !filters.hasEmail || 
        (lead.email && lead.email.trim() !== '')
      
      const matchesLocation = !filters.location || 
        lead.location?.toLowerCase().includes(filters.location.toLowerCase()) ||
        lead.city?.toLowerCase().includes(filters.location.toLowerCase()) ||
        lead.state?.toLowerCase().includes(filters.location.toLowerCase()) ||
        lead.country?.toLowerCase().includes(filters.location.toLowerCase())
      
      return matchesSearch && matchesICPScore && matchesEmailStatus && matchesHasEmail && matchesLocation
    })
    
    // Apply sorting
    filtered.sort((a, b) => {
      let aValue, bValue
      
      switch (filters.sortBy) {
        case 'created_at':
          aValue = new Date(a.created_at).getTime()
          bValue = new Date(b.created_at).getTime()
          break
        case 'full_name':
          aValue = a.full_name?.toLowerCase() || ''
          bValue = b.full_name?.toLowerCase() || ''
          break
        case 'company_name':
          aValue = a.company_name?.toLowerCase() || ''
          bValue = b.company_name?.toLowerCase() || ''
          break
        case 'icp_percentage':
          aValue = a.icp_percentage || 0
          bValue = b.icp_percentage || 0
          break
        default:
          aValue = a.created_at
          bValue = b.created_at
      }
      
      if (filters.sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1
      } else {
        return aValue < bValue ? 1 : -1
      }
    })
    
    setFilteredLeads(filtered)
  }

  const handleRefresh = () => {
    fetchLeads()
    setRefreshTrigger(prev => prev + 1)
  }

  const handleEmailSent = (leadId: string) => {
    setLeads(prev => prev.map(lead => 
      lead.id === leadId 
        ? { ...lead, email_status: 'sent' as const }
        : lead
    ))
    setShowEmailModal(false)
    setSelectedLead(null)
    toast.success('Email sent successfully!')
  }

  const getEmailStatusBadge = (status: string) => {
    switch (status) {
      case 'available':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">Available</span>
      case 'sent':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">Sent</span>
      case 'bounced':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">Bounced</span>
      case 'not_available':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">No Email</span>
      default:
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">Unknown</span>
    }
  }

  const getICPGradeBadge = (grade: string, score: number) => {
    const colorClass = score >= 80 ? 'badge-success' : 
                      score >= 60 ? 'badge-warning' : 'badge-error'
    return <span className={`badge ${colorClass}`}>{grade}</span>
  }

  // Get unique values for filter dropdowns
  const uniqueLocations = Array.from(new Set(leads.flatMap(lead => [lead.location, lead.city, lead.state, lead.country]).filter(Boolean))).sort()

  return (
    <div className="p-6 max-w-full mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Database className="h-8 w-8 text-primary-600" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Leads Database</h1>
            <p className="text-gray-600">Manage and track your lead generation results</p>
          </div>
        </div>
        <button
          onClick={handleRefresh}
          className="btn-secondary flex items-center gap-2"
          disabled={isLoading}
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Lead Metrics */}
      <LeadMetrics className="mb-6" refreshTrigger={refreshTrigger} />

      {/* Filters */}
      <div className="card mb-6">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters
          </h3>
        </div>

        {/* Search */}
        <div className="mb-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search leads by name, company, or job title..."
              value={filters.search}
              onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
              className="input-field pl-10"
            />
          </div>
        </div>

        {
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* ICP Percentage Range */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  ICP Percentage Range
                </label>
                <div className="space-y-2">
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={filters.icpScoreMin}
                    onChange={(e) => setFilters(prev => ({ 
                      ...prev, 
                      icpScoreMin: Number(e.target.value) 
                    }))}
                    className="w-full"
                  />
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={filters.icpScoreMax}
                    onChange={(e) => setFilters(prev => ({ 
                      ...prev, 
                      icpScoreMax: Number(e.target.value) 
                    }))}
                    className="w-full"
                  />
                  <div className="text-sm text-gray-600">
                    {filters.icpScoreMin}% - {filters.icpScoreMax}%
                  </div>
                </div>
              </div>

              {/* Has Email Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email Availability
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="hasEmail"
                    checked={filters.hasEmail}
                    onChange={(e) => setFilters(prev => ({ ...prev, hasEmail: e.target.checked }))}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label htmlFor="hasEmail" className="text-sm text-gray-700">
                    Only show leads with email
                  </label>
                </div>
                
              </div>
                {/* Email Status Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email Status
                </label>
                <select
                  value={filters.emailStatus}
                  onChange={(e) => setFilters(prev => ({ ...prev, emailStatus: e.target.value }))}
                  className="input-field"
                >
                  <option value="">All Statuses</option>
                  <option value="available">Available</option>
                  <option value="sent">Sent</option>
                  <option value="bounced">Bounced</option>
                  <option value="not_available">No Email</option>
                </select>
              </div>

              {/* Sort By */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Sort By
                </label>
                <select
                  value={filters.sortBy}
                  onChange={(e) => setFilters(prev => ({ ...prev, sortBy: e.target.value }))}
                  className="input-field"
                >
                  <option value="created_at">Date Created</option>
                  <option value="full_name">Name</option>
                  <option value="company_name">Company</option>
                  <option value="icp_percentage">ICP Score</option>
                </select>
                <div className="mt-2">
                  <label className="flex items-center space-x-2">
                    <input
                      type="radio"
                      name="sortOrder"
                      value="desc"
                      checked={filters.sortOrder === 'desc'}
                      onChange={(e) => setFilters(prev => ({ ...prev, sortOrder: 'desc' }))}
                      className="text-primary-600 focus:ring-primary-500"
                    />
                    <span className="text-sm text-gray-700">
                      {filters.sortBy === 'full_name' || filters.sortBy === 'company_name' 
                        ? 'Z-A' 
                        : filters.sortBy === 'icp_percentage' 
                        ? 'Most to Least' 
                        : 'Newest First'
                      }
                    </span>
                  </label>
                  <label className="flex items-center space-x-2">
                    <input
                      type="radio"
                      name="sortOrder"
                      value="asc"
                      checked={filters.sortOrder === 'asc'}
                      onChange={(e) => setFilters(prev => ({ ...prev, sortOrder: 'asc' }))}
                      className="text-primary-600 focus:ring-primary-500"
                    />
                    <span className="text-sm text-gray-700">
                      {filters.sortBy === 'full_name' || filters.sortBy === 'company_name' 
                        ? 'A-Z' 
                        : filters.sortBy === 'icp_percentage' 
                        ? 'Least to Most' 
                        : 'Oldest First'
                      }
                    </span>
                  </label>
                </div>
              </div>

              {/* Clear Filters */}
              <div className="flex items-end">
                <button
                  onClick={() => setFilters({
                    search: '',
                    icpScoreMin: 0,
                    icpScoreMax: 100,
                    emailStatus: '',
                    hasEmail: true,
                    location: '',
                    sortBy: 'created_at',
                    sortOrder: 'desc'
                  })}
                  className="btn-secondary w-full"
                >
                  Clear Filters
                </button>
              </div>

            </div>

           
              {/* Location Filter */}
              {/* <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Location
                </label>
                <select
                  value={filters.location}
                  onChange={(e) => setFilters(prev => ({ ...prev, location: e.target.value }))}
                  className="input-field"
                >
                  <option value="">All Locations</option>
                  {uniqueLocations.map(location => (
                    <option key={location} value={location}>{location}</option>
                  ))}
                </select>
              </div> */}



              {/* Company Size Filter */}
              {/* <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Company Size
                </label>
                <select
                  value={filters.companySize}
                  onChange={(e) => setFilters(prev => ({ ...prev, companySize: e.target.value }))}
                  className="input-field"
                >
                  <option value="">All Sizes</option>
                  {uniqueCompanySizes.map(size => (
                    <option key={size} value={size}>{size}</option>
                  ))}
                </select>
              </div> */}

            
            </div>
          
        }
      </div>

      {/* Results Summary */}
      <div className="mb-4">
        <p className="text-sm text-gray-600">
          Showing {filteredLeads.length} of {leads.length} leads
        </p>
      </div>

      {/* Leads Table */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            <span className="ml-2 text-gray-600">Loading leads...</span>
          </div>
        ) : filteredLeads.length === 0 ? (
          <div className="text-center py-12">
            <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No leads found
            </h3>
            <p className="text-gray-600">
              {leads.length === 0 
                ? 'Start by generating some leads from the Lead Generation page.'
                : 'Try adjusting your filters to see more results.'
              }
            </p>
          </div>
        ) : (
          <>
            {/* Desktop Table View */}
            <div className="hidden lg:block overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Lead Info
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Contact
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Company
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Company Social
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Location
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      ICP
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredLeads.map((lead) => (
                    <tr key={lead.id} className="hover:bg-gray-50">
                      <td className="px-3 py-4">
                        <div className="text-sm font-medium text-gray-900">
                          {lead.full_name}
                        </div>
                        <div className="text-xs text-gray-500">
                          {lead.job_title}
                        </div>
                        {lead.linkedin_url && (
                          <a
                            href={lead.linkedin_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-blue-600 hover:text-blue-800 inline-flex items-center gap-1 mt-1"
                          >
                            <ExternalLink className="h-3 w-3" />
                            LinkedIn
                          </a>
                        )}
                      </td>
                      <td className="px-3 py-4">
                        {lead.email && (
                          <div className="text-xs text-gray-900">{lead.email}</div>
                        )}
                        {lead.phone_number && (
                          <div className="text-xs text-gray-500">{lead.phone_number}</div>
                        )}
                      </td>
                      <td className="px-3 py-4">
                        <div className="text-xs font-medium text-gray-900">
                          {lead.company_name}
                        </div>
                        {lead.company_industry && (
                          <div className="text-xs text-gray-500">{lead.company_industry}</div>
                        )}
                        <div className="flex gap-2 mt-1">
                          {lead.company_linkedin && (
                            <a
                              href={lead.company_linkedin}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-blue-600 hover:text-blue-800 inline-flex items-center gap-1"
                            >
                              <ExternalLink className="h-3 w-3" />
                              LinkedIn
                            </a>
                          )}
                          {lead.company_website && (
                            <a
                              href={lead.company_website}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-blue-600 hover:text-blue-800"
                            >
                              Website
                            </a>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-4">
                        <div className="flex gap-2">
                          {lead.company_twitter && (
                            <a
                              href={lead.company_twitter.startsWith('http') ? lead.company_twitter : `https://twitter.com/${lead.company_twitter.replace('@', '')}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-blue-600 hover:text-blue-800 inline-flex items-center gap-1"
                              title="Twitter"
                            >
                              <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"/>
                              </svg>
                            </a>
                          )}
                          {lead.company_facebook && (
                            <a
                              href={lead.company_facebook.startsWith('http') ? lead.company_facebook : `https://facebook.com/${lead.company_facebook}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-blue-600 hover:text-blue-800 inline-flex items-center gap-1"
                              title="Facebook"
                            >
                              <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                              </svg>
                            </a>
                          )}
                          {!lead.company_twitter && !lead.company_facebook && (
                            <span className="text-xs text-gray-400">N/A</span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-4">
                        {lead.location && (
                          <div className="text-xs text-gray-900">{lead.location}</div>
                        )}
                      </td>
                      <td className="px-3 py-4">
                        <div className="flex items-center gap-2">
                          <div className="text-xs text-gray-900">
                            {lead.icp_percentage ? `${lead.icp_percentage}%` : 'N/A'}
                          </div>
                          {lead.icp_grade && (
                            <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium ${
                              lead.icp_grade === 'A+' ? 'bg-green-100 text-green-800' :
                              lead.icp_grade === 'A' ? 'bg-green-100 text-green-800' :
                              lead.icp_grade === 'B' ? 'bg-yellow-100 text-yellow-800' :
                              lead.icp_grade === 'C' ? 'bg-orange-100 text-orange-800' :
                              'bg-red-100 text-red-800'
                            }`}>
                              {lead.icp_grade}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-4">
                        {getEmailStatusBadge(lead.email_status)}
                      </td>
                      <td className="px-3 py-4">
                        {lead.email && lead.email_status !== 'sent' && (
                          <button
                            onClick={() => {
                              setSelectedLead(lead)
                              setShowEmailModal(true)
                            }}
                            className="text-primary-600 hover:text-primary-900 flex items-center gap-1 text-xs"
                          >
                            <Mail className="h-3 w-3" />
                            Email
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Card View */}
            <div className="lg:hidden space-y-4">
              {filteredLeads.map((lead) => (
                <div key={lead.id} className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                  {/* Header */}
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex-1">
                      <h3 className="text-sm font-medium text-gray-900">{lead.full_name}</h3>
                      <p className="text-xs text-gray-500">{lead.job_title}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {lead.icp_grade && (
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          lead.icp_grade === 'A+' ? 'bg-green-100 text-green-800' :
                          lead.icp_grade === 'A' ? 'bg-green-100 text-green-800' :
                          lead.icp_grade === 'B' ? 'bg-yellow-100 text-yellow-800' :
                          lead.icp_grade === 'C' ? 'bg-orange-100 text-orange-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {lead.icp_grade}
                        </span>
                      )}
                      {getEmailStatusBadge(lead.email_status)}
                    </div>
                  </div>

                  {/* Company Info */}
                  <div className="mb-3">
                    <div className="text-xs font-medium text-gray-900">{lead.company_name}</div>
                    {lead.company_industry && (
                      <div className="text-xs text-gray-500">{lead.company_industry}</div>
                    )}
                    {lead.location && (
                      <div className="text-xs text-gray-500">{lead.location}</div>
                    )}
                    <div className="flex gap-3 mt-1">
                      {lead.company_linkedin && (
                        <a
                          href={lead.company_linkedin}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:text-blue-800 inline-flex items-center gap-1"
                        >
                          <ExternalLink className="h-3 w-3" />
                          Company LinkedIn
                        </a>
                      )}
                      {lead.company_website && (
                        <a
                          href={lead.company_website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:text-blue-800"
                        >
                          Website
                        </a>
                      )}
                    </div>
                  </div>

                  {/* Company Social */}
                  <div className="mb-3">
                    <div className="text-xs font-medium text-gray-700 mb-1">Social Media:</div>
                    <div className="flex gap-3">
                      {lead.company_twitter && (
                        <a
                          href={lead.company_twitter.startsWith('http') ? lead.company_twitter : `https://twitter.com/${lead.company_twitter.replace('@', '')}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:text-blue-800 inline-flex items-center gap-1"
                        >
                          <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"/>
                          </svg>
                          Twitter
                        </a>
                      )}
                      {lead.company_facebook && (
                        <a
                          href={lead.company_facebook.startsWith('http') ? lead.company_facebook : `https://facebook.com/${lead.company_facebook}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:text-blue-800 inline-flex items-center gap-1"
                        >
                          <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                          </svg>
                          Facebook
                        </a>
                      )}
                      {!lead.company_twitter && !lead.company_facebook && (
                        <span className="text-xs text-gray-400">N/A</span>
                      )}
                    </div>
                  </div>

                  {/* Contact Info */}
                  <div className="mb-3">
                    {lead.email && (
                      <div className="text-xs text-gray-900">{lead.email}</div>
                    )}
                    {lead.phone_number && (
                      <div className="text-xs text-gray-500">{lead.phone_number}</div>
                    )}
                  </div>

                  {/* ICP Score */}
                  <div className="mb-3">
                    <span className="text-xs text-gray-500">ICP Score: </span>
                    <span className="text-xs text-gray-900">
                      {lead.icp_percentage ? `${lead.icp_percentage}%` : 'N/A'}
                    </span>
                  </div>

                  {/* Actions */}
                  <div className="flex justify-between items-center pt-3 border-t border-gray-100">
                    <div className="flex gap-3">
                      {lead.linkedin_url && (
                        <a
                          href={lead.linkedin_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:text-blue-800 inline-flex items-center gap-1"
                        >
                          <ExternalLink className="h-3 w-3" />
                          LinkedIn
                        </a>
                      )}
                      {lead.company_website && (
                        <a
                          href={lead.company_website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:text-blue-800"
                        >
                          Website
                        </a>
                      )}
                    </div>
                    {lead.email && lead.email_status !== 'sent' && (
                      <button
                        onClick={() => {
                          setSelectedLead(lead)
                          setShowEmailModal(true)
                        }}
                        className="text-primary-600 hover:text-primary-900 flex items-center gap-1 text-xs"
                      >
                        <Mail className="h-3 w-3" />
                        Email
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Email Modal */}
      {showEmailModal && selectedLead && (
        <EmailModal
          lead={selectedLead}
          onClose={() => {
            setShowEmailModal(false)
            setSelectedLead(null)
          }}
          onEmailSent={handleEmailSent}
        />
      )}
    </div>
  )
}