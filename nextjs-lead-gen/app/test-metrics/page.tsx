'use client'

import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import apiClient from '@/lib/api-client'

export default function TestMetricsPage() {
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const { user, session } = useAuth()

  const testMetricsAPI = async () => {
    setLoading(true)
    setResult(null)
    
    try {
      console.log('🔍 Testing metrics API...')
      console.log('👤 Current user:', user?.email)
      console.log('🔑 Session exists:', !!session)
      console.log('🔑 Access token exists:', !!session?.access_token)
      
      const response = await apiClient.getLeadMetrics('30d')
      console.log('📊 Full response:', response)
      
      setResult({
        success: true,
        data: response.data,
        status: response.status
      })
    } catch (error: any) {
      console.error('❌ Error:', error)
      setResult({
        success: false,
        error: error.message,
        response: error.response?.data,
        status: error.response?.status
      })
    } finally {
      setLoading(false)
    }
  }

  const testDirectAPI = async () => {
    setLoading(true)
    setResult(null)
    
    try {
      console.log('🔍 Testing direct API call...')
      
      const response = await fetch('/api/leads/metrics?timeRange=30d', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': session?.access_token ? `Bearer ${session.access_token}` : ''
        }
      })
      
      console.log('📊 Response status:', response.status)
      console.log('📊 Response headers:', Object.fromEntries(response.headers.entries()))
      
      const data = await response.json()
      console.log('📊 Response data:', data)
      
      setResult({
        success: response.ok,
        data,
        status: response.status,
        method: 'direct'
      })
    } catch (error: any) {
      console.error('❌ Direct API Error:', error)
      setResult({
        success: false,
        error: error.message,
        method: 'direct'
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Metrics API Test</h1>
      
      <div className="mb-6 p-4 bg-gray-100 rounded">
        <h2 className="text-lg font-semibold mb-2">Authentication Status</h2>
        <p><strong>User:</strong> {user?.email || 'Not logged in'}</p>
        <p><strong>Session:</strong> {session ? 'Active' : 'None'}</p>
        <p><strong>Access Token:</strong> {session?.access_token ? 'Present' : 'Missing'}</p>
      </div>
      
      <div className="space-x-4 mb-6">
        <button
          onClick={testMetricsAPI}
          disabled={loading}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
        >
          {loading ? 'Testing...' : 'Test via ApiClient'}
        </button>
        
        <button
          onClick={testDirectAPI}
          disabled={loading}
          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
        >
          {loading ? 'Testing...' : 'Test Direct API'}
        </button>
      </div>
      
      {result && (
        <div className="mt-6">
          <h2 className="text-lg font-semibold mb-2">Result</h2>
          <pre className="bg-gray-100 p-4 rounded overflow-auto text-sm">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}