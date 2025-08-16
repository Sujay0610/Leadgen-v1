'use client'

import { useState, useEffect, useRef } from 'react'
import { useForm } from 'react-hook-form'
import { Search, Loader2, Info } from 'lucide-react'
import { toast } from 'react-hot-toast'
import apiClient from '@/lib/api-client'

interface LeadGenerationFormProps {
  leadsPerQuery: number
  onLeadsGenerated: () => void
}

interface FormData {
  method: 'apollo' | 'google_apify'
  jobTitle: string
  location: string
  industry: string
  companySizes: string[]
}

const presetJobTitles = [
  'Operations Head',
  'Operations Manager', 
  'Plant Manager',
  'Production Engineer',
  'Facility Manager',
  'Service Head',
  'Asset Manager',
  'Maintenance Manager',
  'Operations Director',
  'COO'
]

const presetLocations = [
  'United States',
  'Canada',
  'United Kingdom',
  'Australia',
  'Singapore',
  'India'
]

const presetIndustries = [
  'Manufacturing',
  'Industrial Automation',
  'Consumer Electronics'
]

const companySizeOptions = [
  { value: '1,10', label: '1-10 employees' },
  { value: '11,20', label: '11-20 employees' },
  { value: '21,50', label: '21-50 employees' },
  { value: '51,100', label: '51-100 employees' },
  { value: '101,200', label: '101-200 employees' },
  { value: '201,500', label: '201-500 employees' },
  { value: '501,1000', label: '501-1000 employees' }
]

export default function LeadGenerationForm({ leadsPerQuery, onLeadsGenerated }: LeadGenerationFormProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [generationResult, setGenerationResult] = useState<{
    success: boolean
    message: string
    leadsGenerated: number
    timestamp: string
  } | null>(null)
  const [useCustomJobTitle, setUseCustomJobTitle] = useState(false)
  const [useCustomLocation, setUseCustomLocation] = useState(false)
  const [useCustomIndustry, setUseCustomIndustry] = useState(false)
  
  // Status updates for real-time feedback
  const [statusUpdates, setStatusUpdates] = useState<string[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  
  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<FormData>({
    defaultValues: {
      method: 'apollo',
      companySizes: ['1,10', '11,20', '21,50', '51,100']
    }
  })

  const selectedMethod = watch('method')

  // Cleanup SSE connection on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
    }
  }, [])

  // Function to start SSE connection for status updates
  const startStatusUpdates = (sessionId: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    const eventSource = new EventSource(`http://localhost:8000/api/generate-leads/status?session_id=${sessionId}`)
    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      try {
        const statusData = JSON.parse(event.data)
        setStatusUpdates(prev => [...prev, statusData.message])
        
        // Show toast for important updates
        if (statusData.type === 'profiles_found') {
          toast.success(`🔍 Found ${statusData.profiles_count} profiles`)
        } else if (statusData.type === 'apify_enrichment_started') {
          toast.info(`🔄 Starting enrichment for ${statusData.total_profiles} profiles`)
        } else if (statusData.type === 'profile_enriched') {
          toast.success(`✅ Enriched: ${statusData.profile_name}`)
        }
      } catch (error) {
        console.error('Error parsing SSE data:', error)
      }
    }

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error)
      eventSource.close()
      eventSourceRef.current = null
    }

    eventSource.addEventListener('close', () => {
      eventSource.close()
      eventSourceRef.current = null
    })
  }

  const onSubmit = async (data: FormData) => {
    setIsLoading(true)
    setGenerationResult(null)
    setStatusUpdates([])
    
    // Generate session ID for status tracking
    const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    setCurrentSessionId(sessionId)
    
    // Start SSE connection for real-time updates
    startStatusUpdates(sessionId)
    
    try {
      // Validate required fields
      if (!data.jobTitle || !data.location || !data.industry) {
        toast.error('Please provide a job title, location, and industry.')
        return
      }

      // Format data for API
      const leadGenParams = {
        method: data.method,
        jobTitles: [data.jobTitle],
        locations: [data.location],
        industries: [data.industry],
        companySizes: data.companySizes,
        limit: leadsPerQuery,
        session_id: sessionId
      }

      const response = await apiClient.generateLeads(leadGenParams)
      const result = response.data

      if (result.status === 'success') {
        const leadsCount = result.leads_generated || 0
        setGenerationResult({
          success: true,
          message: result.message || 'Leads generated successfully!',
          leadsGenerated: leadsCount,
          timestamp: new Date().toISOString()
        })
        toast.success(`✅ Generated ${leadsCount} leads successfully!`)
        onLeadsGenerated()
      } else {
        setGenerationResult({
          success: false,
          message: result.message || 'Failed to generate leads',
          leadsGenerated: 0,
          timestamp: new Date().toISOString()
        })
        toast.error(`❌ Error: ${result.message || 'Failed to generate leads'}`)
      }
    } catch (error: any) {
      console.error('Error generating leads:', error)
      const errorMessage = error.response?.data?.message || error.message || 'Failed to generate leads'
      setGenerationResult({
        success: false,
        message: errorMessage,
        leadsGenerated: 0,
        timestamp: new Date().toISOString()
      })
      toast.error('❌ Error generating leads. Please try again.')
    } finally {
      setIsLoading(false)
      // Close SSE connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
      setCurrentSessionId(null)
    }
  }

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <Search className="h-5 w-5 text-primary-600" />
        <h2 className="text-lg font-semibold text-gray-900">Direct Lead Search</h2>
      </div>
      
      <div className="mb-4 p-3 bg-blue-50 rounded-lg">
        <p className="text-xs text-blue-800 mb-2">
          Generate leads using Apollo.io or Google Search + Apify enrichment
        </p>
        <p className="text-xs text-blue-700">
          💡 For best results, use specific locations and job titles.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* Method Selection */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-2">
            🔧 Method
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            <label className="flex items-center gap-2 p-2 border rounded cursor-pointer hover:bg-gray-50 text-xs">
              <input
                type="radio"
                value="apollo"
                {...register('method')}
                className="text-xs"
              />
              <div>
                <div className="font-medium text-gray-900">Apollo.io</div>
                <div className="text-xs text-gray-600">Fast, structured data</div>
              </div>
            </label>
            <label className="flex items-center gap-2 p-2 border rounded cursor-pointer hover:bg-gray-50 text-xs">
              <input
                type="radio"
                value="google_apify"
                {...register('method')}
                className="text-xs"
              />
              <div>
                <div className="font-medium text-gray-900">Google + Apify</div>
                <div className="text-xs text-gray-600">Custom search</div>
              </div>
            </label>
          </div>
        </div>

        {/* Search Criteria Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Job Title */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              👔 Job Title
            </label>
            {!useCustomJobTitle ? (
              <div>
                <select
                  {...register('jobTitle', { required: 'Job title is required' })}
                  className="input-field text-xs"
                >
                  <option value="">Select job title</option>
                  {presetJobTitles.map((title) => (
                    <option key={title} value={title}>{title}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => setUseCustomJobTitle(true)}
                  className="mt-1 text-xs text-primary-600 hover:text-primary-700"
                >
                  Custom
                </button>
              </div>
            ) : (
              <div>
                <input
                  type="text"
                  placeholder="Custom job title"
                  {...register('jobTitle', { required: 'Job title is required' })}
                  className="input-field text-xs"
                />
                <button
                  type="button"
                  onClick={() => {
                    setUseCustomJobTitle(false)
                    setValue('jobTitle', '')
                  }}
                  className="mt-1 text-xs text-primary-600 hover:text-primary-700"
                >
                  Preset
                </button>
              </div>
            )}
            {errors.jobTitle && (
              <p className="mt-1 text-xs text-error-600">{errors.jobTitle.message}</p>
            )}
          </div>

          {/* Location */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              📍 Location
            </label>
            {!useCustomLocation ? (
              <div>
                <select
                  {...register('location', { required: 'Location is required' })}
                  className="input-field text-xs"
                >
                  <option value="">Select location</option>
                  {presetLocations.map((location) => (
                    <option key={location} value={location}>{location}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => setUseCustomLocation(true)}
                  className="mt-1 text-xs text-primary-600 hover:text-primary-700"
                >
                  Custom
                </button>
              </div>
            ) : (
              <div>
                <input
                  type="text"
                  placeholder="Custom location"
                  {...register('location', { required: 'Location is required' })}
                  className="input-field text-xs"
                />
                <button
                  type="button"
                  onClick={() => {
                    setUseCustomLocation(false)
                    setValue('location', '')
                  }}
                  className="mt-1 text-xs text-primary-600 hover:text-primary-700"
                >
                  Preset
                </button>
              </div>
            )}
            {errors.location && (
              <p className="mt-1 text-xs text-error-600">{errors.location.message}</p>
            )}
          </div>

          {/* Industry */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              🏭 Industry
            </label>
            {!useCustomIndustry ? (
              <div>
                <select
                  {...register('industry', { required: 'Industry is required' })}
                  className="input-field text-xs"
                >
                  <option value="">Select industry</option>
                  {presetIndustries.map((industry) => (
                    <option key={industry} value={industry}>{industry}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => setUseCustomIndustry(true)}
                  className="mt-1 text-xs text-primary-600 hover:text-primary-700"
                >
                  Custom
                </button>
              </div>
            ) : (
              <div>
                <input
                  type="text"
                  placeholder="Custom industry"
                  {...register('industry', { required: 'Industry is required' })}
                  className="input-field text-xs"
                />
                <button
                  type="button"
                  onClick={() => {
                    setUseCustomIndustry(false)
                    setValue('industry', '')
                  }}
                  className="mt-1 text-xs text-primary-600 hover:text-primary-700"
                >
                  Preset
                </button>
              </div>
            )}
            {errors.industry && (
              <p className="mt-1 text-xs text-error-600">{errors.industry.message}</p>
            )}
          </div>
        </div>

        {/* Company Size - Only for Apollo */}
        {selectedMethod === 'apollo' ? (
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              🏢 Company Size (Apollo Only)
            </label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {companySizeOptions.map((option) => (
                <label key={option.value} className="flex items-center gap-1 text-xs">
                  <input
                    type="checkbox"
                    value={option.value}
                    {...register('companySizes')}
                    className="rounded border-gray-300 text-xs"
                  />
                  <span className="text-xs text-gray-700">{option.label}</span>
                </label>
              ))}
            </div>
          </div>
        ) : (
          <div className="p-2 bg-blue-50 rounded">
            <div className="flex items-center gap-1">
              <Info className="h-3 w-3 text-blue-600" />
              <span className="text-xs text-blue-800">
                Company size filtering not available for Google Search
              </span>
            </div>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full btn-primary flex items-center justify-center gap-2 text-sm py-2"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              🚀 Generate Leads
            </>
          )}
        </button>
      </form>

      {/* Real-time Status Updates */}
      {isLoading && statusUpdates.length > 0 && (
        <div className="mt-6 p-4 bg-gray-50 rounded-lg border">
          <div className="flex items-center gap-2 mb-3">
            <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
            <h3 className="font-semibold text-gray-900">Live Status Updates</h3>
          </div>
          <div className="max-h-40 overflow-y-auto space-y-1">
            {statusUpdates.map((update, index) => (
              <div key={index} className="text-sm text-gray-700 p-2 bg-white rounded border-l-2 border-blue-400">
                {update}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Generation Results */}
      {generationResult && (
        <div className="mt-6 p-4 rounded-lg border">
          <div className={`flex items-center gap-2 mb-3 ${
            generationResult.success ? 'text-green-700' : 'text-red-700'
          }`}>
            <div className={`w-3 h-3 rounded-full ${
              generationResult.success ? 'bg-green-500' : 'bg-red-500'
            }`} />
            <h3 className="font-semibold">
              {generationResult.success ? '✅ Lead Generation Completed' : '❌ Lead Generation Failed'}
            </h3>
          </div>
          
          <div className="space-y-2">
            <p className="text-sm text-gray-600">{generationResult.message}</p>
            
            {generationResult.success && generationResult.leadsGenerated > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                <div className="bg-blue-50 p-3 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">
                    {generationResult.leadsGenerated}
                  </div>
                  <div className="text-sm text-blue-600">Leads Generated</div>
                </div>
                <div className="bg-green-50 p-3 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">
                    {new Date(generationResult.timestamp).toLocaleTimeString()}
                  </div>
                  <div className="text-sm text-green-600">Generated At</div>
                </div>
                <div className="bg-purple-50 p-3 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">
                    {leadsPerQuery}
                  </div>
                  <div className="text-sm text-purple-600">Requested Count</div>
                </div>
              </div>
            )}
            
            {generationResult.success && (
              <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-700">
                  💡 <strong>Next Steps:</strong> Visit the <strong>Leads Dashboard</strong> to view, filter, and manage your newly generated leads.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}