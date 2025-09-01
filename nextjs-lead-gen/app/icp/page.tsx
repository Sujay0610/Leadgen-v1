'use client'

import React, { useState, useEffect } from 'react'
import { Loader2, Settings, Save, RotateCcw, Info, AlertCircle, Mail, ExternalLink } from 'lucide-react'
import { toast } from 'react-hot-toast'
import apiClient from '@/lib/api-client'

interface ICPPromptData {
  prompt: string
  default_values: {
    target_roles: string
    target_industries: string
    target_company_sizes: string
    target_locations: string
    target_seniority: string
  }
}

export default function ICPPage() {
  const [promptData, setPromptData] = useState<ICPPromptData | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState('prompt')

  // Form states for placeholder values
  const [targetRoles, setTargetRoles] = useState('')
  const [targetIndustries, setTargetIndustries] = useState('')
  const [targetCompanySizes, setTargetCompanySizes] = useState('')
  const [targetLocations, setTargetLocations] = useState('')
  const [targetSeniority, setTargetSeniority] = useState('')
  const [customPrompt, setCustomPrompt] = useState('')

  // Email configuration states
  const [resendApiKey, setResendApiKey] = useState('')
  const [fromEmail, setFromEmail] = useState('')
  const [webhookSecret, setWebhookSecret] = useState('')

  useEffect(() => {
    loadICPPrompt()
  }, [])

  const loadICPPrompt = async () => {
    try {
      setLoading(true)
      console.log('Loading ICP prompt...')
      const response = await apiClient.getICPPrompt()
      console.log('ICP prompt response:', response)
      
      if (response.status === 'success' && response.data?.prompt) {
        // Robustly resolve prompt and default values regardless of backend shape
        let prompt = response.data?.prompt ?? ''
        let default_values: Record<string, any> = response.data?.default_values ?? {}

        if (prompt && typeof prompt === 'object') {
          // Attempt to unwrap nested structures
          const inner = (prompt as any).data || prompt
          prompt = inner.prompt || JSON.stringify(prompt, null, 2)
        }
        if (!default_values || typeof default_values !== 'object') {
          default_values = {}
        }

        console.log('Resolved prompt (string):', typeof prompt, prompt)
        console.log('Resolved default_values:', default_values)
        
        setPromptData({
          prompt: String(prompt),
          default_values: {
            target_roles: default_values.target_roles || '',
            target_industries: default_values.target_industries || '',
            target_company_sizes: default_values.target_company_sizes || '',
            target_locations: default_values.target_locations || '',
            target_seniority: default_values.target_seniority || ''
          }
        })
        
        // Set form values
        setCustomPrompt(String(prompt))
        setTargetRoles(default_values.target_roles || '')
        setTargetIndustries(default_values.target_industries || '')
        setTargetCompanySizes(default_values.target_company_sizes || '')
        setTargetLocations(default_values.target_locations || '')
        setTargetSeniority(default_values.target_seniority || '')
      } else {
        console.log('No existing ICP prompt found, loading defaults')
        // Load default prompt if no custom prompt exists
        try {
          const defaultResponse = await fetch('/api/icp/default-prompt')
          if (defaultResponse.ok) {
            const defaultData = await defaultResponse.json()
            setCustomPrompt(defaultData.prompt)
            setTargetRoles(defaultData.default_values.target_roles)
            setTargetIndustries(defaultData.default_values.target_industries)
            setTargetCompanySizes(defaultData.default_values.target_company_sizes)
            setTargetLocations(defaultData.default_values.target_locations)
            setTargetSeniority(defaultData.default_values.target_seniority)
          }
        } catch (defaultError) {
          console.error('Error loading default prompt:', defaultError)
          // Set empty defaults if both API calls fail
          setCustomPrompt('')
          setTargetRoles('')
          setTargetIndustries('')
          setTargetCompanySizes('')
          setTargetLocations('')
          setTargetSeniority('')
        }
      }
    } catch (error) {
      console.error('Error loading ICP prompt:', error)
      toast.error('Failed to load ICP configuration')
    } finally {
      setLoading(false)
    }
  }

  const saveICPPrompt = async () => {
    try {
      setSaving(true)
      
      const data = {
        prompt: customPrompt,
        default_values: {
          target_roles: targetRoles,
          target_industries: targetIndustries,
          target_company_sizes: targetCompanySizes,
          target_locations: targetLocations,
          target_seniority: targetSeniority
        }
      }
      
      const response = await apiClient.updateICPPrompt(data)
      
      if (response.status === 'success') {
        toast.success('ICP configuration saved successfully')
        await loadICPPrompt() // Reload to get updated data
      } else {
        toast.error(response.message || 'Failed to save ICP configuration')
      }
    } catch (error) {
      console.error('Error saving ICP prompt:', error)
      toast.error('Failed to save ICP configuration')
    } finally {
      setSaving(false)
    }
  }

  const resetToDefaults = async () => {
    try {
      // Fetch the actual default prompt from backend
      const response = await fetch('/api/icp/default-prompt')
      if (response.ok) {
        const defaultData = await response.json()
        setCustomPrompt(defaultData.prompt)
        setTargetRoles(defaultData.default_values.target_roles)
        setTargetIndustries(defaultData.default_values.target_industries)
        setTargetCompanySizes(defaultData.default_values.target_company_sizes)
        setTargetLocations(defaultData.default_values.target_locations)
        setTargetSeniority(defaultData.default_values.target_seniority)
        toast.success('Reset to default values')
      } else {
        // Fallback to hardcoded defaults if API fails
        const defaultPrompt = `You are an AI assistant that evaluates LinkedIn profiles against specific Ideal Customer Profile (ICP) criteria.

Your task is to analyze the provided profile data and determine how well this person fits our target customer profile.

ICP DEFINITIONS:

**Operations ICP:**
- Industries: Manufacturing, Industrial Automation, Heavy Equipment, CNC, Robotics, Facility Management, Fleet Ops
- Roles: Operations Head, Plant Manager, Maintenance Lead, Production Engineer, Digital Transformation Officer
- Seniority: Manager level or above
- Company Maturity: Founded before 2020 (≥5 years old)

**Field Service ICP:**
- Industries: Ghost kitchens, cloud kitchens, commercial real estate, managed appliances, kitchen automation, hotels
- Roles: Facility Manager, Maintenance Coordinator, Service Head, Asset Manager
- Seniority: Manager level or above
- Company Maturity: Founded before 2021 (≥3 years old)

SCORING CRITERIA (Weighted):
1. Industry Fit (30%): How well does their industry align with our target ICPs?
2. Role Fit (30%): How relevant is their job title/role to our solution?
3. Company Maturity (20%): Does the company meet our maturity requirements?
4. Decision Maker (20%): Are they likely to have decision-making authority?

Profile to analyze:
{profile_json}

Provide your analysis in the following JSON format:
{
  "overall_score": <number between 0-100>,
  "best_icp_match": "operations" or "field_service" or "none",
  "breakdown": {
    "industry_fit": <score 0-100>,
    "role_fit": <score 0-100>,
    "company_maturity": <score 0-100>,
    "decision_maker": <score 0-100>
  },
  "reasoning": "<detailed explanation of scoring>",
  "recommendation": "<actionable next steps>"
}`
        
        setCustomPrompt(defaultPrompt)
        setTargetRoles('Operations Manager, Facility Manager, Plant Manager, Production Supervisor, Maintenance Lead')
        setTargetIndustries('Manufacturing, Industrial Equipment, Automotive, Food Processing, Heavy Equipment')
        setTargetCompanySizes('Mid-size companies with 50-1000 employees')
        setTargetLocations('North America, Europe, Global markets')
        setTargetSeniority('Manager level and above, Director level, VP level, C-level executives')
        toast.success('Reset to default values')
      }
    } catch (error) {
      console.error('Error resetting to defaults:', error)
      toast.error('Failed to reset to defaults')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading ICP configuration...</span>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">ICP Configuration</h1>
          <p className="text-gray-600 mt-2">
            Configure your Ideal Customer Profile using a customizable AI prompt with placeholders
          </p>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={resetToDefaults} 
            className="flex items-center px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset
          </button>
          <button 
            onClick={saveICPPrompt} 
            disabled={saving}
            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            Save Configuration
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'prompt', label: 'AI Prompt Configuration', icon: Settings },
            { id: 'placeholders', label: 'Placeholder Values', icon: Info },
            { id: 'email', label: 'Email Configuration', icon: Mail }
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'prompt' && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-2">AI Prompt Configuration</h2>
          <p className="text-gray-600 mb-6">
            Customize the AI prompt used for scoring leads against your ICP criteria. Use placeholders to make the prompt dynamic.
          </p>
          
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              ICP Scoring Prompt
            </label>
            <textarea
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              rows={25}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
              placeholder="Enter your custom ICP scoring prompt..."
            />
          </div>
          
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start">
              <Info className="h-5 w-5 text-blue-600 mt-0.5 mr-2 flex-shrink-0" />
              <div>
                <h4 className="font-medium text-blue-900 mb-2">Available Placeholders:</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <code className="bg-blue-100 px-2 py-1 rounded text-blue-800">{`{target_roles}`}</code>
                  <code className="bg-blue-100 px-2 py-1 rounded text-blue-800">{`{target_industries}`}</code>
                  <code className="bg-blue-100 px-2 py-1 rounded text-blue-800">{`{target_company_sizes}`}</code>
                  <code className="bg-blue-100 px-2 py-1 rounded text-blue-800">{`{target_locations}`}</code>
                  <code className="bg-blue-100 px-2 py-1 rounded text-blue-800">{`{target_seniority}`}</code>
                  <code className="bg-blue-100 px-2 py-1 rounded text-blue-800">{`{full_name}`}</code>
                  <code className="bg-blue-100 px-2 py-1 rounded text-blue-800">{`{job_title}`}</code>
                  <code className="bg-blue-100 px-2 py-1 rounded text-blue-800">{`{company_name}`}</code>
                  <code className="bg-blue-100 px-2 py-1 rounded text-blue-800">{`{company_size}`}</code>
                  <code className="bg-blue-100 px-2 py-1 rounded text-blue-800">{`{location}`}</code>
                  <code className="bg-blue-100 px-2 py-1 rounded text-blue-800">{`{headline}`}</code>
                  <code className="bg-blue-100 px-2 py-1 rounded text-blue-800">{`{summary}`}</code>
                </div>
                <p className="text-blue-700 mt-2 text-sm">
                  The first 5 placeholders can be customized in the "Placeholder Values" tab. The rest are automatically filled from lead data.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'placeholders' && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-2">Placeholder Values</h2>
          <p className="text-gray-600 mb-6">
            Configure the values that will replace the placeholders in your ICP prompt. These define your ideal customer profile criteria.
          </p>
          
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Target Roles <code className="text-blue-600">{`{target_roles}`}</code>
              </label>
              <textarea
                value={targetRoles}
                onChange={(e) => setTargetRoles(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Operations Manager, Facility Manager, Plant Manager, Production Supervisor"
              />
              <p className="text-sm text-gray-500 mt-1">
                Describe the job titles and roles you want to target
              </p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Target Industries <code className="text-blue-600">{`{target_industries}`}</code>
              </label>
              <textarea
                value={targetIndustries}
                onChange={(e) => setTargetIndustries(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Manufacturing, Industrial Equipment, Automotive, Food Processing"
              />
              <p className="text-sm text-gray-500 mt-1">
                Specify the industries you want to focus on
              </p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Target Company Sizes <code className="text-blue-600">{`{target_company_sizes}`}</code>
              </label>
              <textarea
                value={targetCompanySizes}
                onChange={(e) => setTargetCompanySizes(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Mid-size companies with 50-1000 employees, Enterprise companies with 1000+ employees"
              />
              <p className="text-sm text-gray-500 mt-1">
                Define your ideal company size ranges
              </p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Target Locations <code className="text-blue-600">{`{target_locations}`}</code>
              </label>
              <textarea
                value={targetLocations}
                onChange={(e) => setTargetLocations(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., North America, United States, California, Remote"
              />
              <p className="text-sm text-gray-500 mt-1">
                Specify target geographic locations or regions
              </p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Target Seniority <code className="text-blue-600">{`{target_seniority}`}</code>
              </label>
              <textarea
                value={targetSeniority}
                onChange={(e) => setTargetSeniority(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Manager level or above, Director level, C-level executives"
              />
              <p className="text-sm text-gray-500 mt-1">
                Define the seniority levels you want to target
              </p>
            </div>
          </div>
          
          <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex items-start">
              <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5 mr-2 flex-shrink-0" />
              <div>
                <h4 className="font-medium text-yellow-900 mb-1">How it works:</h4>
                <p className="text-yellow-800 text-sm">
                  When analyzing leads, the AI will replace these placeholders in your prompt with the values you specify here. 
                  This allows you to easily update your ICP criteria without modifying the entire prompt structure.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Email Configuration Tab */}
      {activeTab === 'email' && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-2">Email Configuration</h2>
          <p className="text-gray-600 mb-6">
            Configure your Resend email settings for sending emails and tracking events.
          </p>

          <div className="space-y-6">
            {/* Setup Instructions */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start">
                <Info className="h-5 w-5 text-blue-600 mt-0.5 mr-2 flex-shrink-0" />
                <div>
                  <h4 className="font-medium text-blue-900 mb-2">Setup Instructions:</h4>
                  <ol className="text-blue-800 text-sm space-y-1 list-decimal list-inside">
                    <li>Create a Resend account at <a href="https://resend.com" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline inline-flex items-center">resend.com <ExternalLink className="h-3 w-3 ml-1" /></a></li>
                    <li>Get your API key from the Resend dashboard</li>
                    <li>Set up your domain in Resend for email sending</li>
                    <li>Configure webhooks for email event tracking</li>
                    <li>Update the configuration below with your settings</li>
                  </ol>
                </div>
              </div>
            </div>

            {/* Resend API Key */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Resend API Key
              </label>
              <input
                type="password"
                value={resendApiKey}
                onChange={(e) => setResendApiKey(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="re_xxxxxxxxxxxxxxxxxxxxxxxxxx"
              />
              <p className="text-sm text-gray-500 mt-1">
                Your Resend API key for sending emails. Get this from your Resend dashboard.
              </p>
            </div>

            {/* From Email */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                From Email Address
              </label>
              <input
                type="email"
                value={fromEmail}
                onChange={(e) => setFromEmail(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="noreply@yourdomain.com"
              />
              <p className="text-sm text-gray-500 mt-1">
                The email address that will appear as the sender. Must be from a verified domain in Resend.
              </p>
            </div>

            {/* Webhook Secret */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Webhook Secret
              </label>
              <input
                type="password"
                value={webhookSecret}
                onChange={(e) => setWebhookSecret(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="whsec_xxxxxxxxxxxxxxxxxxxxxxxxxx"
              />
              <p className="text-sm text-gray-500 mt-1">
                Webhook secret for verifying email event callbacks from Resend.
              </p>
            </div>

            {/* Webhook Setup Instructions */}
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-start">
                <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5 mr-2 flex-shrink-0" />
                <div>
                  <h4 className="font-medium text-yellow-900 mb-2">Webhook Configuration:</h4>
                  <div className="text-yellow-800 text-sm space-y-2">
                    <p>To track email events (opens, clicks, bounces), set up a webhook in your Resend dashboard:</p>
                    <div className="bg-yellow-100 p-2 rounded border">
                      <p className="font-mono text-xs">Webhook URL: {window.location.origin}/api/webhooks/resend</p>
                    </div>
                    <p>Select the following events: delivered, opened, clicked, bounced, complained</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Current Backend Configuration */}
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <div className="flex items-start">
                <Settings className="h-5 w-5 text-gray-600 mt-0.5 mr-2 flex-shrink-0" />
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Current Backend Configuration:</h4>
                  <p className="text-gray-700 text-sm mb-2">
                    These settings are currently stored in the backend .env file. In the future, they will be configurable through this interface.
                  </p>
                  <div className="space-y-1 text-sm">
                    <div className="flex items-center">
                      <span className="font-medium text-gray-600 w-32">FROM_EMAIL:</span>
                      <code className="bg-gray-100 px-2 py-1 rounded text-xs">onsend@resend.dev</code>
                    </div>
                    <div className="flex items-center">
                      <span className="font-medium text-gray-600 w-32">API Key:</span>
                      <code className="bg-gray-100 px-2 py-1 rounded text-xs">re_8uGbCoNy_***</code>
                    </div>
                    <div className="flex items-center">
                      <span className="font-medium text-gray-600 w-32">Webhook Secret:</span>
                      <code className="bg-gray-100 px-2 py-1 rounded text-xs">whsec_dokUgAo***</code>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Save Button for Email Config */}
            <div className="flex justify-end">
              <button 
                onClick={() => toast('Email configuration will be implemented in a future update', {
                  icon: '🔔',
                  duration: 4000
                })}
                className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Save className="h-4 w-4 mr-2" />
                Save Email Configuration
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}