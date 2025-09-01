'use client'

import { useState, useEffect } from 'react'
import { 
  Mail, 
  Send, 
  Eye, 
  RefreshCw, 
  User, 
  Building, 
  Briefcase,
  MapPin,
  AtSign,
  TestTube,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react'
import { toast } from 'react-hot-toast'
import apiClient from '@/lib/api-client'

interface Lead {
  id: string
  full_name: string
  first_name: string
  last_name: string
  email: string
  job_title: string
  company_name: string
  linkedin_url: string
  icp_score: number
  location: string
}

interface EmailTemplate {
  id: string
  subject: string
  body: string
  persona: string
  stage: string
}

interface GeneratedEmail {
  subject: string
  body: string
  status: string
  message?: string
}

interface TestResult {
  type: 'success' | 'error' | 'warning'
  message: string
  timestamp: string
}

export default function EmailTestingPage() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null)
  const [selectedTemplate, setSelectedTemplate] = useState<EmailTemplate | null>(null)
  const [generatedEmail, setGeneratedEmail] = useState<GeneratedEmail | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [testResults, setTestResults] = useState<TestResult[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [customLeadData, setCustomLeadData] = useState({
    full_name: 'John Smith',
    first_name: 'John',
    email: 'john.smith@example.com',
    job_title: 'Operations Manager',
    company_name: 'TechCorp Industries',
    location: 'San Francisco, CA'
  })

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setIsLoading(true)
    try {
      const [leadsResponse, templatesResponse] = await Promise.all([
        apiClient.getLeads({ limit: 20 }),
        apiClient.getEmailTemplates()
      ])

      // Handle leads response
      if (leadsResponse.data?.status === 'success') {
        const leadsData = leadsResponse.data.leads || leadsResponse.data.data || []
        setLeads(leadsData)
        if (leadsData.length > 0) {
          setSelectedLead(leadsData[0])
        }
      }

      // Handle templates response
      if (templatesResponse.status === 'success') {
        const templatesData = templatesResponse.templates || templatesResponse.data || []
        setTemplates(templatesData)
        if (templatesData.length > 0) {
          setSelectedTemplate(templatesData[0])
        }
      }
    } catch (error) {
      console.error('Error fetching data:', error)
      addTestResult('error', 'Failed to load leads and templates')
    } finally {
      setIsLoading(false)
    }
  }

  const addTestResult = (type: 'success' | 'error' | 'warning', message: string) => {
    const result: TestResult = {
      type,
      message,
      timestamp: new Date().toLocaleTimeString()
    }
    setTestResults(prev => [result, ...prev.slice(0, 9)]) // Keep last 10 results
  }

  const generateEmailWithTemplate = async () => {
    if (!selectedTemplate || !selectedLead) {
      addTestResult('error', 'Please select both a lead and template')
      return
    }

    setIsGenerating(true)
    try {
      // Use the new backend API for template-based generation
      const leadData = {
        fullName: selectedLead.full_name,
        firstName: selectedLead.first_name,
        lastName: selectedLead.last_name,
        jobTitle: selectedLead.job_title,
        companyName: selectedLead.company_name,
        email: selectedLead.email,
        location: selectedLead.location,
        linkedinUrl: selectedLead.linkedin_url,
        icpScore: selectedLead.icp_score
      }

      const response = await apiClient.generateEmail({
        leadName: selectedLead.full_name,
        leadCompany: selectedLead.company_name,
        leadTitle: selectedLead.job_title,
        templateId: selectedTemplate.id,
        leadData: leadData
      })

      if (response.data?.status === 'success') {
        const result: GeneratedEmail = {
          subject: response.data.data.subject,
          body: response.data.data.body,
          status: 'success'
        }
        setGeneratedEmail(result)
        addTestResult('success', `AI-personalized email generated using template: ${selectedTemplate.persona} - ${selectedTemplate.stage}`)
      } else {
        // Fallback to simple template replacement if API fails
        let subject = selectedTemplate.subject
        let body = selectedTemplate.body

        const replacements = {
          '{{firstName}}': leadData.firstName || leadData.fullName?.split(' ')[0] || 'there',
          '{{fullName}}': leadData.fullName || 'there',
          '{{companyName}}': leadData.companyName || 'your company',
          '{{jobTitle}}': leadData.jobTitle || 'your role',
          '{{location}}': leadData.location || 'your area'
        }

        Object.entries(replacements).forEach(([placeholder, value]) => {
          subject = subject.replace(new RegExp(placeholder, 'g'), value)
          body = body.replace(new RegExp(placeholder, 'g'), value)
        })

        const result: GeneratedEmail = {
          subject,
          body,
          status: 'success'
        }
        setGeneratedEmail(result)
        addTestResult('warning', `Fallback template generation used: ${selectedTemplate.persona} - ${selectedTemplate.stage}`)
      }
    } catch (error) {
      console.error('Error generating email:', error)
      addTestResult('error', 'Failed to generate email with template - using fallback')
      
      // Fallback to simple template replacement
      try {
        let subject = selectedTemplate.subject
        let body = selectedTemplate.body

        const leadData = {
          fullName: selectedLead.full_name,
          firstName: selectedLead.first_name,
          jobTitle: selectedLead.job_title,
          companyName: selectedLead.company_name,
          location: selectedLead.location
        }

        const replacements = {
          '{{firstName}}': leadData.firstName || leadData.fullName?.split(' ')[0] || 'there',
          '{{fullName}}': leadData.fullName || 'there',
          '{{companyName}}': leadData.companyName || 'your company',
          '{{jobTitle}}': leadData.jobTitle || 'your role',
          '{{location}}': leadData.location || 'your area'
        }

        Object.entries(replacements).forEach(([placeholder, value]) => {
          subject = subject.replace(new RegExp(placeholder, 'g'), value)
          body = body.replace(new RegExp(placeholder, 'g'), value)
        })

        const result: GeneratedEmail = {
          subject,
          body,
          status: 'success'
        }
        setGeneratedEmail(result)
        addTestResult('warning', 'Used basic template replacement (API unavailable)')
      } catch (fallbackError) {
        addTestResult('error', 'All email generation methods failed')
      }
    } finally {
      setIsGenerating(false)
    }
  }

  const generateEmailWithAI = async () => {
    const leadToUse = selectedLead || {
      ...customLeadData,
      id: 'custom',
      last_name: customLeadData.full_name.split(' ').slice(1).join(' '),
      linkedin_url: '',
      icp_score: 75
    }

    setIsGenerating(true)
    try {
      const response = await apiClient.generateEmail({
        leadName: leadToUse.full_name,
        leadCompany: leadToUse.company_name,
        leadTitle: leadToUse.job_title,
        emailType: 'cold_outreach',
        tone: 'professional'
      })

      if (response.data?.status === 'success') {
        setGeneratedEmail({
          subject: response.data.data?.subject || `Quick question about ${leadToUse.company_name}`,
          body: response.data.data?.body || response.data.data?.content,
          status: 'success'
        })
        addTestResult('success', 'AI-generated email created successfully')
      } else {
        addTestResult('error', response.data?.message || 'Failed to generate AI email')
      }
    } catch (error) {
      console.error('Error generating AI email:', error)
      addTestResult('error', 'AI email generation failed - API may not be available')
      
      // Fallback to mock generation
      const mockEmail = {
        subject: `Quick question about ${leadToUse.company_name}`,
        body: `Hi ${leadToUse.first_name},\n\nI noticed ${leadToUse.company_name} is in the ${leadToUse.job_title} space. We help companies like yours streamline operations and reduce manual processes.\n\nWould you be open to a brief conversation about how we could help ${leadToUse.company_name} improve efficiency?\n\nBest regards,\nYour Name`,
        status: 'success'
      }
      setGeneratedEmail(mockEmail)
      addTestResult('warning', 'Used fallback email generation (AI API unavailable)')
    } finally {
      setIsGenerating(false)
    }
  }

  const simulateEmailSend = async () => {
    if (!generatedEmail) {
      addTestResult('error', 'No email to send - generate one first')
      return
    }

    const leadToUse = selectedLead || {
      ...customLeadData,
      id: 'custom',
      last_name: customLeadData.full_name.split(' ').slice(1).join(' '),
      linkedin_url: '',
      icp_score: 75
    }

    setIsSending(true)
    try {
      // Simulate email sending with validation
      await new Promise(resolve => setTimeout(resolve, 2000)) // Simulate API delay
      
      // Mock validation checks
      const validations = [
        { check: 'Email format', valid: leadToUse.email.includes('@') },
        { check: 'Subject line', valid: generatedEmail.subject.length > 0 },
        { check: 'Email body', valid: generatedEmail.body.length > 10 },
        { check: 'Recipient name', valid: leadToUse.full_name.length > 0 }
      ]

      const allValid = validations.every(v => v.valid)
      
      if (allValid) {
        addTestResult('success', `Email simulation sent to ${leadToUse.email}`)
        addTestResult('success', 'All validation checks passed')
      } else {
        const failedChecks = validations.filter(v => !v.valid).map(v => v.check)
        addTestResult('error', `Validation failed: ${failedChecks.join(', ')}`)
      }
    } catch (error) {
      addTestResult('error', 'Email sending simulation failed')
    } finally {
      setIsSending(false)
    }
  }

  const testEmailConfig = async () => {
    try {
      const response = await fetch('/api/email/send?action=config')
      const data = await response.json()
      
      if (data.status === 'success') {
        const config = data.config
        addTestResult('success', `Email config loaded: ${config.fromEmail}`)
        addTestResult(config.resendConfigured ? 'success' : 'warning', 
          `Resend API: ${config.resendConfigured ? 'Configured' : 'Not configured'}`)
        addTestResult('success', `Daily limit: ${config.maxDailyEmails} emails`)
      } else {
        addTestResult('error', 'Failed to load email configuration')
      }
    } catch (error) {
      addTestResult('error', 'Email configuration test failed')
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-gray-600">Loading email testing interface...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <TestTube className="h-8 w-8 text-blue-600" />
            Email Testing Lab
          </h1>
          <p className="text-gray-600 mt-2">
            Test email generation, templates, and sending functionality with mock data
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Lead Selection */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <User className="h-5 w-5 text-blue-600" />
              Select Lead
            </h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Database Leads
                </label>
                <select 
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={selectedLead?.id || ''}
                  onChange={(e) => {
                    const lead = leads.find(l => l.id === e.target.value)
                    setSelectedLead(lead || null)
                  }}
                >
                  <option value="">Select a lead...</option>
                  {leads.map(lead => (
                    <option key={lead.id} value={lead.id}>
                      {lead.full_name} - {lead.company_name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="border-t pt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Or Use Custom Data
                </label>
                <div className="space-y-3">
                  <input
                    type="text"
                    placeholder="Full Name"
                    className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    value={customLeadData.full_name}
                    onChange={(e) => setCustomLeadData(prev => ({ ...prev, full_name: e.target.value, first_name: e.target.value.split(' ')[0] }))}
                  />
                  <input
                    type="email"
                    placeholder="Email"
                    className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    value={customLeadData.email}
                    onChange={(e) => setCustomLeadData(prev => ({ ...prev, email: e.target.value }))}
                  />
                  <input
                    type="text"
                    placeholder="Job Title"
                    className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    value={customLeadData.job_title}
                    onChange={(e) => setCustomLeadData(prev => ({ ...prev, job_title: e.target.value }))}
                  />
                  <input
                    type="text"
                    placeholder="Company Name"
                    className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    value={customLeadData.company_name}
                    onChange={(e) => setCustomLeadData(prev => ({ ...prev, company_name: e.target.value }))}
                  />
                </div>
              </div>

              {(selectedLead || customLeadData.full_name) && (
                <div className="bg-gray-50 p-3 rounded-lg">
                  <h3 className="font-medium text-gray-900 mb-2">Selected Lead:</h3>
                  <div className="text-sm text-gray-600 space-y-1">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4" />
                      {selectedLead?.full_name || customLeadData.full_name}
                    </div>
                    <div className="flex items-center gap-2">
                      <AtSign className="h-4 w-4" />
                      {selectedLead?.email || customLeadData.email}
                    </div>
                    <div className="flex items-center gap-2">
                      <Briefcase className="h-4 w-4" />
                      {selectedLead?.job_title || customLeadData.job_title}
                    </div>
                    <div className="flex items-center gap-2">
                      <Building className="h-4 w-4" />
                      {selectedLead?.company_name || customLeadData.company_name}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Email Generation */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Mail className="h-5 w-5 text-blue-600" />
              Generate Email
            </h2>

            <div className="space-y-4">
              {/* Template Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email Template
                </label>
                <select 
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={selectedTemplate?.id || ''}
                  onChange={(e) => {
                    const template = templates.find(t => t.id === e.target.value)
                    setSelectedTemplate(template || null)
                  }}
                >
                  <option value="">Select template...</option>
                  {templates.map(template => (
                    <option key={template.id} value={template.id}>
                      {template.persona} - {template.stage}
                    </option>
                  ))}
                </select>
              </div>

              {/* Generation Buttons */}
              <div className="space-y-3">
                <button
                  onClick={generateEmailWithTemplate}
                  disabled={isGenerating || !selectedTemplate}
                  className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isGenerating ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                  Generate with Template
                </button>

                <button
                  onClick={generateEmailWithAI}
                  disabled={isGenerating}
                  className="w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isGenerating ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <TestTube className="h-4 w-4" />
                  )}
                  Generate with AI
                </button>

                <button
                  onClick={testEmailConfig}
                  className="w-full bg-gray-600 text-white py-3 px-4 rounded-lg hover:bg-gray-700 flex items-center justify-center gap-2"
                >
                  <AlertCircle className="h-4 w-4" />
                  Test Email Config
                </button>
              </div>

              {/* Email Preview */}
              {generatedEmail && (
                <div className="border-t pt-4">
                  <h3 className="font-medium text-gray-900 mb-3">Generated Email:</h3>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Subject:</label>
                      <div className="p-2 bg-gray-50 rounded border text-sm">
                        {generatedEmail.subject}
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Body:</label>
                      <div className="p-3 bg-gray-50 rounded border text-sm whitespace-pre-wrap max-h-40 overflow-y-auto">
                        {generatedEmail.body}
                      </div>
                    </div>
                    <button
                      onClick={simulateEmailSend}
                      disabled={isSending}
                      className="w-full bg-purple-600 text-white py-2 px-4 rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {isSending ? (
                        <RefreshCw className="h-4 w-4 animate-spin" />
                      ) : (
                        <Send className="h-4 w-4" />
                      )}
                      Simulate Send
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Test Results */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              Test Results
            </h2>

            <div className="space-y-3 max-h-96 overflow-y-auto">
              {testResults.length === 0 ? (
                <p className="text-gray-500 text-sm">No test results yet. Start testing!</p>
              ) : (
                testResults.map((result, index) => (
                  <div key={index} className={`p-3 rounded-lg border-l-4 ${
                    result.type === 'success' ? 'bg-green-50 border-green-400' :
                    result.type === 'error' ? 'bg-red-50 border-red-400' :
                    'bg-yellow-50 border-yellow-400'
                  }`}>
                    <div className="flex items-start gap-2">
                      {result.type === 'success' ? (
                        <CheckCircle className="h-4 w-4 text-green-600 mt-0.5" />
                      ) : result.type === 'error' ? (
                        <XCircle className="h-4 w-4 text-red-600 mt-0.5" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-yellow-600 mt-0.5" />
                      )}
                      <div className="flex-1">
                        <p className={`text-sm font-medium ${
                          result.type === 'success' ? 'text-green-800' :
                          result.type === 'error' ? 'text-red-800' :
                          'text-yellow-800'
                        }`}>
                          {result.message}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          {result.timestamp}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            <button
              onClick={() => setTestResults([])}
              className="w-full mt-4 bg-gray-100 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-200 text-sm"
            >
              Clear Results
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}