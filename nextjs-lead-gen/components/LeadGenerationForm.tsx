'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useForm } from 'react-hook-form'
import { Search, Loader2, Info } from 'lucide-react'
import apiClient from '@/lib/api-client'
import { useAuth } from '@/contexts/AuthContext'

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
  const { user, session } = useAuth()
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
  const [statusUpdates, setStatusUpdates] = useState<Array<{message: string, type?: string, url?: string}>>([])  
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [currentPhase, setCurrentPhase] = useState<string>('')
  const [estimatedTimeRemaining, setEstimatedTimeRemaining] = useState<number | null>(null)
  const [startTime, setStartTime] = useState<number | null>(null)
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const isPollingRef = useRef<boolean>(false)
  const statusUpdatesRef = useRef<HTMLDivElement>(null)
  const statusListRef = useRef<HTMLDivElement>(null)
  
  // Auto-scroll to bottom when new status updates are added
  useEffect(() => {
    if (statusListRef.current) {
      statusListRef.current.scrollTop = statusListRef.current.scrollHeight
    }
  }, [statusUpdates])

  // Update ETA countdown timer
  useEffect(() => {
    if (!isLoading || estimatedTimeRemaining === null) return

    const timer = setInterval(() => {
      setEstimatedTimeRemaining(prev => {
        if (prev === null || prev <= 0) return 0
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [isLoading, estimatedTimeRemaining])
  
  // Helper function to add unique status updates
  const addUniqueStatusUpdate = useCallback((newUpdate: {message: string, type?: string, url?: string}) => {
    console.log('Adding status update:', newUpdate)
    setStatusUpdates(prev => {
      // Check if this exact message already exists
      const exists = prev.some(update => update.message === newUpdate.message)
      if (exists) {
        console.log('Duplicate status update, skipping:', newUpdate.message)
        return prev // Don't add duplicate
      }
      const updated = [...prev, newUpdate]
      console.log('Status updates array updated:', updated)
      return updated
    })
  }, [])
  
  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<FormData>({
    defaultValues: {
      method: 'apollo',
      companySizes: ['1,10', '11,20', '21,50', '51,100']
    }
  })

  const selectedMethod = watch('method')

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        console.log('Cleaning up polling on unmount')
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
        isPollingRef.current = false
      }
    }
  }, [])

  // Function to start polling for status updates
  const startStatusPolling = async (sessionId: string) => {
    try {
      // Stop existing polling if any
      if (pollingIntervalRef.current) {
        console.log('Stopping existing polling')
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }

      isPollingRef.current = true
      
      // Status polling started - no need to show this to user

      const pollStatus = async () => {
        if (!isPollingRef.current) return

        try {
          console.log(`[POLLING] Making API call to get status for session: ${sessionId}`)
          console.log('[POLLING AUTH] User authenticated:', !!user)
          console.log('[POLLING AUTH] Session exists:', !!session)
          console.log('[POLLING AUTH] Session access token exists:', !!session?.access_token)
          
          const response = await apiClient.getLeadGenerationStatus(sessionId)
          const jsonResp = response.data
          console.log('[POLLING] Raw API response:', jsonResp)
          console.log('[POLLING] Response status:', response.status)
          console.log('[POLLING] Response headers:', response.headers)
          
          // Handle the response structure from backend API
          let statusData = jsonResp?.success ? jsonResp.data : jsonResp
          
          // Additional normalization for backend response format
          if (Array.isArray(statusData)) {
            // If it's an array, take the latest status
            statusData = statusData[statusData.length - 1]
          }
          
          // Debug logging for status updates
          console.log('Raw jsonResp:', jsonResp)
          console.log('Parsed status data:', statusData)
          console.log('Status data type:', statusData?.type)
          console.log('Status data message:', statusData?.message)
          
          // If no status data, skip this iteration
          if (!statusData) {
            console.log('No status data received, skipping...')
            return
          }
          
          // Handle session not found - retry for a while before giving up
          if (statusData.error === 'Session not found' || statusData.status === 'not_found') {
            // Initialize retry counter if not exists
            if (!(pollStatus as any).retryCount) {
              (pollStatus as any).retryCount = 0
            }
            
            (pollStatus as any).retryCount++
            console.log(`Session not found, retry ${(pollStatus as any).retryCount}/10`)
            
            // Give up after 10 retries (20 seconds)
            if ((pollStatus as any).retryCount >= 10) {
              console.log('Session not found after 10 retries, stopping polling')
              setIsLoading(false)
              isPollingRef.current = false
              if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current)
                pollingIntervalRef.current = null
              }
              setCurrentSessionId(null)
            }
            return
          }
          
          // Reset retry counter when session is found
          ;(pollStatus as any).retryCount = 0
          
          // Handle different status types with enhanced messaging
           
           if (statusData.type === 'started') {
             setCurrentPhase('Starting lead generation...')
             setStartTime(Date.now())
             setEstimatedTimeRemaining(120) // 2 minutes initial estimate
             addUniqueStatusUpdate({
               message: `🚀 ${statusData.message}`,
               type: 'started'
             })
           } else if (statusData.type === 'apollo_url_generated') {
            addUniqueStatusUpdate({
              message: '🔗 Generated Apollo search URL',
              type: 'apollo_url',
              url: statusData.apollo_url
            })
          } else if (statusData.type === 'apollo_search_started') {
             setCurrentPhase('Scraping profiles from Apollo.io...')
             setEstimatedTimeRemaining(90)
             addUniqueStatusUpdate({
               message: `🔍 Scraping profiles from Apollo.io`,
               type: 'apollo_search_started'
             })
           } else if (statusData.type === 'profiles_found') {
            const count = statusData.profiles_count ?? statusData.profiles_found
            addUniqueStatusUpdate({
              message: `👥 Found ${count} profiles from Apollo.io`,
              type: 'profiles_found'
            })
          } else if (statusData.type === 'processing_started') {
            addUniqueStatusUpdate({
              message: `⚙️ ${statusData.message || `Processing ${statusData.total_profiles || ''} Apollo profiles`}`,
              type: 'processing_started'
            })
          } else if (statusData.type === 'profile_processed') {
            const progress = Math.round((statusData.current_profile / statusData.total_profiles) * 100)
            addUniqueStatusUpdate({
              message: `🧩 Processed ${statusData.current_profile}/${statusData.total_profiles} (${progress}%)`,
              type: 'profile_processed'
            })
          } else if (statusData.type === 'apollo_search_completed') {
            addUniqueStatusUpdate({
              message: `✅ ${statusData.message || `Successfully processed ${statusData.profiles_processed || ''} Apollo profiles`}`,
              type: 'apollo_search_completed'
            })
          } else if (statusData.type === 'apollo_search_error') {
            addUniqueStatusUpdate({
              message: `❌ ${statusData.message || 'Apollo search error'}`,
              type: 'apollo_search_error'
            })
          } else if (statusData.type === 'google_search_started') {
             setCurrentPhase('Scraping profiles via Google Search...')
             setEstimatedTimeRemaining(120)
             addUniqueStatusUpdate({
               message: `🔍 Scraping profiles via Google Search`,
               type: 'google_search_started'
             })
           } else if (statusData.type === 'google_search_completed') {
            const count = statusData.profiles_found ?? statusData.profiles_count
            addUniqueStatusUpdate({
              message: `🔍 Google search completed: Found ${count} profiles`,
              type: 'google_search_completed'
            })
          } else if (statusData.type === 'apify_enrichment_started') {
             setCurrentPhase('Enriching profile data...')
             setEstimatedTimeRemaining(60)
             addUniqueStatusUpdate({
               message: `🔄 Enriching ${statusData.total_profiles} profiles`,
               type: 'apify_enrichment_started'
             })
           } else if (statusData.type === 'apify_enrichment_progress') {
            const current = statusData.current_profile
            const total = statusData.total_profiles
            const progress = Math.round((current / total) * 100)
            addUniqueStatusUpdate({
              message: `🔄 Enrichment progress: ${current}/${total} (${progress}%)`,
              type: 'apify_enrichment_progress'
            })
          } else if (statusData.type === 'profile_enriched') {
            if (statusData.profile_name) {
              addUniqueStatusUpdate({
                message: `✅ Enriched: ${statusData.profile_name}`,
                type: 'profile_enriched'
              })
            }
          } else if (statusData.type === 'profile_enrichment_error') {
            addUniqueStatusUpdate({
              message: `⚠️ ${statusData.message || 'Error enriching profile'}`,
              type: 'profile_enrichment_error'
            })
          } else if (statusData.type === 'apify_enrichment_completed') {
            addUniqueStatusUpdate({
              message: `✅ ${statusData.message || 'Apify enrichment completed'}`,
              type: 'apify_enrichment_completed'
            })
          } else if (statusData.type === 'icp_scoring_started') {
             setCurrentPhase('ICP Scoring leads...')
             setEstimatedTimeRemaining(30)
             addUniqueStatusUpdate({
               message: `🎯 ICP Scoring leads`,
               type: 'icp_scoring'
             })
           } else if (statusData.type === 'lead_scored') {
            const progress = Math.round((statusData.current_lead / statusData.total_leads) * 100)
            addUniqueStatusUpdate({
              message: `📊 Scoring progress: ${statusData.current_lead}/${statusData.total_leads} (${progress}%)`,
              type: 'progress'
            })
          } else if (statusData.type === 'saving_leads_started') {
             setCurrentPhase('Saving leads to database...')
             setEstimatedTimeRemaining(10)
             addUniqueStatusUpdate({
               message: `💾 Saving leads to database`,
               type: 'saving'
             })
           } else if (statusData.type === 'saving_leads_completed') {
            const saved = statusData.leads_saved
            addUniqueStatusUpdate({
              message: `💾 ${statusData.message || `Successfully saved ${saved ?? ''} leads to database`}`,
              type: 'saving_completed'
            })
          } else if (statusData.type === 'heartbeat') {
            // Keep-alive message from server; don't surface to UI to avoid noise
            console.debug('Polling heartbeat:', statusData.timestamp || Date.now())
          }

          // Finalization/termination cases: stop polling
           if (statusData.type === 'generation_completed') {
             const leadsCount = statusData.total_leads || 0
             setCurrentPhase('Completed!')
             setEstimatedTimeRemaining(0)
             addUniqueStatusUpdate({ message: `🎉 ${statusData.message || 'Generation completed'}`, type: 'completed' })
             
             // Set final generation result
             setGenerationResult({
               success: true,
               message: statusData.message || 'Leads generated successfully!',
               leadsGenerated: leadsCount,
               timestamp: new Date().toISOString()
             })
             
             setIsLoading(false)
             isPollingRef.current = false
             if (pollingIntervalRef.current) {
               clearInterval(pollingIntervalRef.current)
               pollingIntervalRef.current = null
             }
             setCurrentSessionId(null)
             onLeadsGenerated()
           }
          
          if (statusData.type === 'error') {
            addUniqueStatusUpdate({ message: `❌ ${statusData.message || 'An error occurred'}`, type: 'error' })
            setIsLoading(false)
            isPollingRef.current = false
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current)
              pollingIntervalRef.current = null
            }
            setCurrentSessionId(null)
          }
        } catch (error) {
          console.error('Error polling status:', error)
        }
      }

      // Start polling every 2 seconds
      pollingIntervalRef.current = setInterval(pollStatus, 2000)
      
      // Initial poll
      pollStatus()

    } catch (error) {
      console.error('Error setting up status polling:', error)
    }
  }

   const onSubmit = async (data: FormData) => {
      setIsLoading(true)
      setGenerationResult(null)
      setStatusUpdates([])
      setCurrentPhase('')
      setEstimatedTimeRemaining(null)
      setStartTime(null)
     
     // Scroll to status updates section
     setTimeout(() => {
       statusUpdatesRef.current?.scrollIntoView({ behavior: 'smooth' })
     }, 100)
     
     try {
       // Validate required fields
       if (!data.jobTitle || !data.location || !data.industry) {
         // toast.error('Please provide a job title, location, and industry.') // Removed to reduce popup alerts
         return
       }

       console.log('[LEAD_GEN] Starting lead generation with data:', data)
        console.log('[AUTH] User authenticated:', !!user)
        console.log('[AUTH] Session exists:', !!session)
        console.log('[AUTH] User ID:', user?.id)
        console.log('[AUTH] Session access token exists:', !!session?.access_token)
        
        const response = await apiClient.generateLeads({
          method: data.method,
          jobTitles: [data.jobTitle],
          locations: [data.location],
          industries: data.industry ? [data.industry] : [],
          companySizes: data.companySizes,
          limit: leadsPerQuery
        })

        console.log('[LEAD_GEN] Lead generation response:', response)
        console.log('[LEAD_GEN] Response status:', response.status)
        const result = response.data

       if (result.status === 'success') {
          const backendSessionId = result.session_id
          console.log('[LEAD_GEN] Session ID received from backend:', backendSessionId)
          setCurrentSessionId(backendSessionId)
          
          // Start polling for status updates with the correct session ID
          console.log('[LEAD_GEN] Starting status polling for session:', backendSessionId)
          await startStatusPolling(backendSessionId)
          
          // Don't set generationResult here - wait for polling to complete
          // The background task will emit 'generation_completed' when done
          // toast.success(`🚀 Lead generation started successfully!`) // Removed to reduce popup alerts
        } else {
          setGenerationResult({
            success: false,
            message: result.message || 'Failed to generate leads',
            leadsGenerated: 0,
            timestamp: new Date().toISOString()
          })
          // toast.error(`❌ Error: ${result.message || 'Failed to generate leads'}`) // Removed to reduce popup alerts
          setIsLoading(false)
          isPollingRef.current = false
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current)
            pollingIntervalRef.current = null
          }
          setCurrentSessionId(null)
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
       // toast.error('❌ Error generating leads. Please try again.') // Removed to reduce popup alerts
     } finally {
       // Intentionally do NOT set isLoading(false) here; rely on SSE 'generation_completed' or 'error' events
       // Close SSE connection
       // Intentionally do NOT close SSE here; let it run until we receive a final event
       // so that the stream isn't aborted prematurely (which shows as net::ERR_ABORTED in DevTools).
       // If needed, cleanup happens on unmount or when a new session starts.
       // if (eventSourceRef.current) {
       //   intentionalCloseRef.current = true
       //   eventSourceRef.current.close()
       //   eventSourceRef.current = null
       // }
       // setCurrentSessionId(null)
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
          {(isLoading || statusUpdates.length > 0) && (
            <div ref={statusUpdatesRef} className="mt-6 p-4 bg-gray-50 rounded-lg border">
             <div className="flex items-center justify-between mb-3">
               <div className="flex items-center gap-2">
                 {isLoading ? (
                   <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                 ) : (
                   <span className="inline-block w-3 h-3 rounded-full bg-green-500" />
                 )}
                 <h3 className="font-semibold text-gray-900">
                   {isLoading ? 'Live Status Updates' : 'Status Updates (completed)'}
                 </h3>
               </div>
               {isLoading && estimatedTimeRemaining !== null && (
                 <div className="text-sm text-gray-600">
                   ETA: {estimatedTimeRemaining > 60 ? `${Math.ceil(estimatedTimeRemaining / 60)}m` : `${Math.max(0, estimatedTimeRemaining)}s`}
                 </div>
               )}
             </div>
             {isLoading && currentPhase && (
               <div className="mb-3 p-2 bg-blue-100 rounded text-sm font-medium text-blue-800">
                 {currentPhase}
               </div>
             )}
            <div ref={statusListRef} className="max-h-40 overflow-y-auto space-y-1">
              {statusUpdates.map((update, index) => (
                <div key={index} className="text-sm text-gray-700 p-2 bg-white rounded border-l-2 border-blue-400">
                  <div className="flex items-center justify-between">
                    <span>{update.message}</span>
                    {update.url && (
                      <a 
                        href={update.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="ml-2 text-blue-600 hover:text-blue-800 underline text-xs"
                      >
                        View URL
                      </a>
                    )}
                  </div>
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