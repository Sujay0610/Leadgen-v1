'use client'

import { useState, useEffect } from 'react'
import { X, Mail, Send, Loader2, RefreshCw, Save } from 'lucide-react'
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

  useEffect(() => {
    // Set default email content
    setSubject(`Quick question about ${lead.company_name}`)
    setBody(`Hi ${lead.first_name},

I noticed your role as ${lead.job_title} at ${lead.company_name}.

[Your personalized message here]

Best regards,
[Your name]`)
  }, [lead])

  const handleUseTemplate = async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.generateEmail({
        persona,
        stage,
        leadData: {
          fullName: lead.full_name,
          firstName: lead.first_name,
          jobTitle: lead.job_title,
          companyName: lead.company_name,
          email: lead.email
        }
      })

      const data = response.data

      if (data.status === 'success') {
        setSubject(data.data.subject)
        setBody(data.data.body)
        toast.success('✅ Email generated from templates!')
      } else {
        toast.error(data.message || 'Failed to generate email from template')
      }
    } catch (error: any) {
      console.error('Error using template:', error)
      const errorMessage = error.response?.data?.message || error.message || 'Error generating email from template'
      toast.error(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSaveAsTemplate = async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.createEmailTemplate({
        name: `${persona}_${stage}_template`,
        subject,
        body,
        persona,
        stage,
        isActive: true
      })

      const data = response.data

      if (data.status === 'success') {
        toast.success('✅ Saved as template for future use!')
      } else {
        toast.error(data.message || 'Failed to save template')
      }
    } catch (error: any) {
      console.error('Error saving template:', error)
      const errorMessage = error.response?.data?.message || error.message || 'Error saving template'
      toast.error(errorMessage)
    } finally {
      setIsLoading(false)
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

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <Mail className="h-6 w-6 text-primary-600" />
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                📧 Email for {lead.full_name}
              </h2>
              <p className="text-sm text-gray-600">
                {lead.job_title} at {lead.company_name}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Lead Information */}
          <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
            <div>
              <span className="font-medium text-gray-900">Lead:</span>
              <span className="ml-2 text-gray-700">{lead.full_name} ({lead.job_title})</span>
            </div>
            <div>
              <span className="font-medium text-gray-900">Company:</span>
              <span className="ml-2 text-gray-700">{lead.company_name}</span>
            </div>
          </div>

          {/* Email Status Check */}
          {lead.email_status === 'sent' && (
            <div className="p-4 bg-success-50 border border-success-200 rounded-lg">
              <p className="text-success-800">✅ Email already sent to this lead</p>
            </div>
          )}

          {/* Template Controls */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">✍️ Compose Email</h3>
            
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Persona
                </label>
                <select
                  value={persona}
                  onChange={(e) => setPersona(e.target.value)}
                  className="input-field"
                >
                  <option value="operations_manager">Operations Manager</option>
                  <option value="facility_manager">Facility Manager</option>
                  <option value="maintenance_manager">Maintenance Manager</option>
                  <option value="plant_manager">Plant Manager</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email Stage
                </label>
                <select
                  value={stage}
                  onChange={(e) => setStage(e.target.value)}
                  className="input-field"
                >
                  <option value="initial_outreach">Initial Outreach</option>
                  <option value="follow_up">Follow Up</option>
                  <option value="meeting_request">Meeting Request</option>
                </select>
              </div>
            </div>

            <div className="flex gap-3 mb-4">
              <button
                onClick={handleUseTemplate}
                disabled={isLoading}
                className="btn-secondary flex items-center gap-2"
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                Use Template
              </button>
              <button
                onClick={handleSaveAsTemplate}
                disabled={isLoading}
                className="btn-secondary flex items-center gap-2"
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                Save as Template
              </button>
            </div>
          </div>

          {/* Email Form */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Subject
              </label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="input-field"
                placeholder="Email subject"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Body
              </label>
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                rows={8}
                className="input-field resize-none"
                placeholder="Email body"
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            className="btn-secondary"
          >
            Cancel
          </button>
          <button
            onClick={handleSendEmail}
            disabled={isSending || !subject.trim() || !body.trim()}
            className="btn-primary flex items-center gap-2"
          >
            {isSending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                Send Email
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}