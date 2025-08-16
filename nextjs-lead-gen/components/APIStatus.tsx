'use client'

import { useState, useEffect } from 'react'
import { CheckCircle, XCircle, Key } from 'lucide-react'
import apiClient from '@/lib/api-client'

interface APIStatusProps {
  className?: string
}

interface APIService {
  name: string
  status: boolean
  description: string
}

export default function APIStatus({ className = '' }: APIStatusProps) {
  const [apiServices, setApiServices] = useState<APIService[]>([])

  useEffect(() => {
    // Check API status on component mount
    checkAPIStatus()
  }, [])

  const checkAPIStatus = async () => {
    try {
      // Check backend API status
      const response = await apiClient.getLeadGenerationConfig()
      const data = response.data
      
      if (data.status === 'success' && data.configuration) {
        const config = data.configuration
        setApiServices([
          {
            name: 'OpenAI API',
            status: config.openai_configured || false,
            description: 'AI-powered lead scoring and email generation'
          },
          {
            name: 'Google Search API',
            status: config.google_configured || false,
            description: 'Custom search for lead discovery'
          },
          {
            name: 'Apify API',
            status: config.apify_configured || false,
            description: 'LinkedIn scraping service'
          },
          {
            name: 'Supabase',
            status: config.supabase_configured || false,
            description: 'Database and authentication'
          }
        ])
      } else {
        // Fallback if configuration is not available
        setApiServices([
          { name: 'OpenAI API', status: false, description: 'AI-powered lead scoring and email generation' },
          { name: 'Google Search API', status: false, description: 'Custom search for lead discovery' },
          { name: 'Apify API', status: false, description: 'LinkedIn scraping service' },
          { name: 'Supabase', status: false, description: 'Database and authentication' }
        ])
      }
    } catch (error) {
      console.error('Error checking API status:', error)
      // Set default status if API check fails
      setApiServices([
        { name: 'OpenAI API', status: false, description: 'AI-powered lead scoring and email generation' },
        { name: 'Google Search API', status: false, description: 'Custom search for lead discovery' },
        { name: 'Apify API', status: false, description: 'LinkedIn scraping service' },
        { name: 'Supabase', status: false, description: 'Database and authentication' }
      ])
    }
  }

  return (
    <div className={`card ${className}`}>
      <div className="flex items-center gap-2 mb-4">
        <Key className="h-5 w-5 text-gray-600" />
        <h3 className="text-lg font-semibold text-gray-900">API Status</h3>
      </div>
      
      <div className="space-y-3">
        {apiServices.map((service) => (
          <div key={service.name} className="flex items-start gap-3">
            {service.status ? (
              <CheckCircle className="h-5 w-5 text-success-600 flex-shrink-0 mt-0.5" />
            ) : (
              <XCircle className="h-5 w-5 text-error-600 flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-1 min-w-0">
              <div className="font-medium text-sm text-gray-900">
                {service.name}
              </div>
              <div className="text-xs text-gray-500">
                {service.description}
              </div>
            </div>
          </div>
        ))}
        

      </div>
      
      <button
        onClick={checkAPIStatus}
        className="mt-4 w-full btn-secondary text-sm"
      >
        Refresh Status
      </button>
    </div>
  )
}