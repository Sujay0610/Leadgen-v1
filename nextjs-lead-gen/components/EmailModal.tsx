'use client'

import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { X, Mail, Send, Loader2, RefreshCw, Save, Wand2 } from 'lucide-react'
import { toast } from 'react-hot-toast'
import apiClient from '@/lib/api-client'

interface Lead {
  id: string
  full_name: string
  first_name: string
  last_name: string
  job_title: string
  company_name: string
  email: string
  linkedin_url: string
  company_website: string
  location: string
  icp_score: number
  icp_grade: string
  email_status: string
}

interface EmailModalProps {
  lead: Lead
  onClose: () => void
  onEmailSent: (leadId: string) => void
}

interface EmailTemplate {
  id: string
  subject: string
  body: string
  persona: string
  stage: string
}

export default function EmailModal({ lead, onClose, onEmailSent }: EmailModalProps) {
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [persona, setPersona] = useState('operations_manager')
  const [stage, setStage] = useState('initial_outreach')
  const [isLoading, setIsLoading] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [selectedTemplateId, setSelectedTemplateId] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)

  useEffect(() => {
    // Set default email content
    setSubject(`Quick question about ${lead.company_name}`)
    setBody(`Hi ${lead.first_name},\n\nI noticed your role as ${lead.job_title} at ${lead.company_name}.\n\n[Your personalized message here]\n\nBest regards,\n[Your name]`)
    
    // Fetch templates when modal opens
    fetchTemplates()
  }, [lead.company_name, lead.first_name, lead.job_title])

  const fetchTemplates = async () => {
    try {
      const response = await apiClient.getEmailTemplates()
      // Backend returns {status: 'success', data: [...], count: ...}
      if (response && response.status === 'success' && Array.isArray(response.data)) {
        setTemplates(response.data)
      } else {
        setTemplates([])
      }
    } catch (error) {
      console.error('Error fetching templates:', error)
      toast.error('Failed to fetch email templates')
      setTemplates([])
    }
  }

  const handleGenerateEmail = async () => {
    if (!selectedTemplateId) {
      toast.error('Please select an email template')
      return
    }

    setIsGenerating(true)
    try {
      const response = await apiClient.generateEmail({
        leadName: lead.full_name,
        leadCompany: lead.company_name,
        leadTitle: lead.job_title,
        templateId: selectedTemplateId,
        leadData: {
          fullName: lead.full_name,
          firstName: lead.first_name,
          jobTitle: lead.job_title,
          companyName: lead.company_name,
          email: lead.email
        },
        stage: stage
      })

      const data = response.data

      if (data.status === 'success') {
        setSubject(data.data.subject)
        setBody(data.data.body)
        toast.success('✅ Email generated from template!')
      } else {
        toast.error(data.message || 'Failed to generate email from template')
      }
    } catch (error: any) {
      console.error('Error generating email:', error)
      const errorMessage = error.response?.data?.message || error.message || 'Error generating email from template'
      toast.error(errorMessage)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleGenerateAndSend = async () => {
    if (!selectedTemplateId) {
      toast.error('Please select an email template')
      return
    }

    if (!subject || !body) {
      toast.error('Please generate email content first')
      return
    }

    setIsSending(true)
    try {
      const response = await apiClient.sendEmail({
        to: lead.email,
        subject,
        body,
        leadId: lead.id,
        metadata: {
          templateId: selectedTemplateId,
          persona: persona,
          stage: stage,
          leadData: {
            fullName: lead.full_name,
            firstName: lead.first_name,
            jobTitle: lead.job_title,
            companyName: lead.company_name
          }
        }
      })

      const data = response.data

      if (data.status === 'success') {
        toast.success('📤 Email sent successfully!')
        onEmailSent(lead.id)
      } else {
        toast.error(data.message || 'Failed to send email')
      }
    } catch (error: any) {
      console.error('Error sending email:', error)
      const errorMessage = error.response?.data?.message || error.message || 'Error sending email'
      toast.error(errorMessage)
    } finally {
      setIsSending(false)
    }
  }

  const handleSendEmail = async () => {
    if (!subject.trim() || !body.trim()) {
      toast.error('Please provide both subject and body')
      return
    }

    setIsSending(true)
    try {
      const response = await apiClient.sendEmail({
        to: lead.email,
        subject,
        body,
        leadId: lead.id,
        metadata: {
          leadData: {
            fullName: lead.full_name,
        firstName: lead.first_name,
        jobTitle: lead.job_title,
        companyName: lead.company_name
          }
        }
      })

      const data = response.data

      if (data.status === 'success') {
        toast.success('📤 Email sent successfully!')
        onEmailSent(lead.id)
      } else {
        toast.error(data.message || 'Failed to send email')
      }
    } catch (error: any) {
      console.error('Error sending email:', error)
      const errorMessage = error.response?.data?.message || error.message || 'Error sending email'
      toast.error(errorMessage)
    } finally {
      setIsSending(false)
    }
  }

  const modalContent = (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-primary-600" />
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                📧 Email for {lead.full_name}
              </h2>
              <p className="text-xs text-gray-600">
                {lead.job_title} at {lead.company_name}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="h-4 w-4 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Lead Information */}
          <div className="grid grid-cols-2 gap-3 p-3 bg-gray-50 rounded-lg">
            <div>
              <span className="text-sm font-medium text-gray-900">Lead:</span>
              <span className="ml-1 text-sm text-gray-700">{lead.full_name} ({lead.job_title})</span>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-900">Company:</span>
              <span className="ml-1 text-sm text-gray-700">{lead.company_name}</span>
            </div>
          </div>

          {/* Email Status Check */}
          {lead.email_status === 'sent' && (
            <div className="p-3 bg-success-50 border border-success-200 rounded-lg">
              <p className="text-sm text-success-800">✅ Email already sent to this lead</p>
            </div>
          )}

          {/* Template Controls */}
          <div>
            <h3 className="text-base font-medium text-gray-900 mb-3">✍️ Compose Email</h3>
            
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Select Persona
                </label>
                <select
                  value={persona}
                  onChange={(e) => setPersona(e.target.value)}
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="operations_manager">Operations Manager</option>
                  <option value="facility_manager">Facility Manager</option>
                  <option value="maintenance_manager">Maintenance Manager</option>
                  <option value="plant_manager">Plant Manager</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Email Stage
                </label>
                <select
                  value={stage}
                  onChange={(e) => setStage(e.target.value)}
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="initial_outreach">Initial Outreach</option>
                  <option value="follow_up">Follow Up</option>
                  <option value="meeting_request">Meeting Request</option>
                </select>
              </div>
            </div>

            {/* Template Selection */}
            <div className="mb-4">
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Email Template
              </label>
              <select
                value={selectedTemplateId}
                onChange={(e) => setSelectedTemplateId(e.target.value)}
                className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Select a template</option>
                {Array.isArray(templates) && templates.map(template => (
                  <option key={template.id} value={template.id}>
                    {template.subject}
                  </option>
                ))}
              </select>
            </div>

            {/* Generate Email Button */}
            <div className="mb-4">
              <button
                onClick={handleGenerateEmail}
                disabled={isGenerating || !selectedTemplateId}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white px-3 py-1.5 text-sm rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
              >
                {isGenerating ? (
                  <>
                    <div className="animate-spin rounded-full h-3 w-3 border-2 border-white border-t-transparent"></div>
                    Generating...
                  </>
                ) : (
                  <>
                    <Wand2 className="h-3 w-3" />
                    Generate from Template
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Email Form */}
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Subject
              </label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Email subject"
              />
            </div>
            
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Body
              </label>
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                rows={10}
                className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                placeholder="Email body"
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800 font-medium"
          >
            Cancel
          </button>
          <button
            onClick={handleGenerateAndSend}
            disabled={isSending || !subject.trim() || !body.trim() || !selectedTemplateId}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white px-4 py-1.5 text-sm rounded-lg font-medium transition-colors flex items-center gap-2"
          >
            {isSending ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <Send className="h-3 w-3" />
                Generate & Send
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )

  return typeof document !== 'undefined' ? createPortal(modalContent, document.body) : null
}