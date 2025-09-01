'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2 } from 'lucide-react'
import { toast } from 'react-hot-toast'
import apiClient from '@/lib/api-client'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedMethod, setSelectedMethod] = useState<'apollo' | 'google_apify'>('apollo')
  const [statusUpdates, setStatusUpdates] = useState<string[]>([])
  const [isGeneratingLeads, setIsGeneratingLeads] = useState(false)
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const statusPollingRef = useRef<NodeJS.Timeout | null>(null)

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      const container = messagesEndRef.current.closest('.overflow-y-auto')
      if (container) {
        container.scrollTop = container.scrollHeight
      }
    }
  }

  // Scroll to bottom when messages change (internal chat scrolling only)
  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    // Focus input on mount
    inputRef.current?.focus()
  }, [])

  // Status polling functions
  const startStatusPolling = (sessionId: string) => {
    setCurrentSessionId(sessionId)
    setIsGeneratingLeads(true)
    setStatusUpdates([])
    
    const pollStatus = async () => {
      try {
        const response = await apiClient.getLeadGenerationStatus(sessionId)
        const data = response.data
        
        if (data.success && data.data) {
          const statusData = data.data
          
          // Create detailed status update from backend data
          const timestamp = new Date().toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
          })
          
          let statusMessage = ''
          
          // Handle different status types with detailed information
          if (statusData.type === 'generation_completed') {
            statusMessage = `🎉 Lead generation completed! Generated ${statusData.total_leads || 0} leads`
            setStatusUpdates(prev => [...prev, `[${timestamp}] ${statusMessage}`])
            
            setIsGeneratingLeads(false)
            if (statusPollingRef.current) {
              clearInterval(statusPollingRef.current)
              statusPollingRef.current = null
            }
            return
          }
          
          if (statusData.type === 'error') {
            statusMessage = `❌ Lead generation failed: ${statusData.message}`
            setStatusUpdates(prev => [...prev, `[${timestamp}] ${statusMessage}`])
            
            setIsGeneratingLeads(false)
            if (statusPollingRef.current) {
              clearInterval(statusPollingRef.current)
              statusPollingRef.current = null
            }
            return
          }
          
          // Handle all status types with appropriate icons and formatting
          let statusIcon = '🔄'
          
          switch (statusData.type) {
            case 'apollo_search_started':
              statusIcon = '🔍'
              break
            case 'apollo_url_generated':
              statusIcon = '🔗'
              break
            case 'profiles_found':
              statusIcon = '👥'
              break
            case 'profile_processed':
              statusIcon = '⚙️'
              break
            case 'apollo_search_completed':
              statusIcon = '✅'
              break
            case 'processing_started':
              statusIcon = '🔄'
              break
            case 'icp_scoring_started':
              statusIcon = '🎯'
              break
            case 'lead_scored':
              statusIcon = '📊'
              break
            case 'icp_scoring_completed':
              statusIcon = '✅'
              break
            case 'saving_leads_started':
              statusIcon = '💾'
              break
            case 'saving_leads_completed':
              statusIcon = '✅'
              break
            case 'google_search_started':
              statusIcon = '🔍'
              break
            case 'linkedin_profiles_found':
              statusIcon = '👥'
              break
            case 'enrichment_started':
              statusIcon = '🔄'
              break
            case 'enrichment_completed':
              statusIcon = '✅'
              break
            default:
              statusIcon = '🔄'
          }
          
          // Handle progress updates with detailed backend information
          if (statusData.message) {
            // Extract detailed progress information from backend
            const progressInfo = []
            
            if (statusData.profiles_count && statusData.current_profile) {
              progressInfo.push(`Profiles: ${statusData.current_profile}/${statusData.profiles_count}`)
            }
            
            if (statusData.leads_scored !== undefined) {
              progressInfo.push(`Leads scored: ${statusData.leads_scored}`)
            }
            
            if (statusData.leads_saved !== undefined) {
              progressInfo.push(`Leads saved: ${statusData.leads_saved}`)
            }
            
            if (statusData.eta_text) {
              progressInfo.push(`ETA: ${statusData.eta_text}`)
            }
            
            // Create comprehensive status message with icon
            statusMessage = `${statusIcon} ${statusData.message}`
            if (progressInfo.length > 0) {
              statusMessage += ` (${progressInfo.join(', ')})`
            }
            
            setStatusUpdates(prev => {
              const newUpdate = `[${timestamp}] ${statusMessage}`
              // Avoid duplicate messages
              if (prev[prev.length - 1] !== newUpdate) {
                return [...prev, newUpdate]
              }
              return prev
            })
          }
        }
      } catch (error) {
        console.error('Status polling error:', error)
        const timestamp = new Date().toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        })
        setStatusUpdates(prev => [...prev, `[${timestamp}] ⚠️ Status polling error: ${error}`])
      }
    }
    
    // Start polling immediately
    pollStatus()
    
    // Set up interval for continued polling
    statusPollingRef.current = setInterval(pollStatus, 2000)
  }

  const stopStatusPolling = () => {
    if (statusPollingRef.current) {
      clearInterval(statusPollingRef.current)
      statusPollingRef.current = null
    }
    setIsGeneratingLeads(false)
    setCurrentSessionId(null)
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (statusPollingRef.current) {
        clearInterval(statusPollingRef.current)
      }
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      // Convert messages to the format expected by the API
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }))

      const response = await apiClient.sendChatMessage({
        message: input.trim(),
        conversationHistory,
        context: { 
          leadGenerationMode: true,
          method: selectedMethod
        }
      })

      const data = response.data

      if (data.status === 'success') {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.data.response,
          timestamp: new Date()
        }
        setMessages(prev => [...prev, assistantMessage])
        
        // Check if lead generation was started and we have a session ID
        if (data.data.sessionId && data.data.leadGeneration?.status === 'started') {
          startStatusPolling(data.data.sessionId)
        }
      } else {
// toast.error(`Error: ${data.message || 'Failed to get response'}`) // Removed to reduce popup alerts
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `Sorry, I encountered an error: ${data.message || 'Please try again.'}`,
          timestamp: new Date()
        }
        setMessages(prev => [...prev, errorMessage])
      }
    } catch (error: any) {
      console.error('Chat error:', error)
      const errorMessage = error.response?.data?.message || error.message || 'Connection error'
      // toast.error(`Failed to send message: ${errorMessage}`) // Removed to reduce popup alerts
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered a connection error. Please try again.',
        timestamp: new Date()
      }
        setMessages(prev => [...prev, errorMsg])
      } finally {
      setIsLoading(false)
    }
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="card h-[600px] flex flex-col">
      <div className="flex items-center justify-between mb-4 pb-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <Bot className="h-6 w-6 text-primary-600" />
          <h2 className="text-xl font-semibold text-gray-900">Chat with Lead Generation Joe</h2>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Method:</label>
          <select
            value={selectedMethod}
            onChange={(e) => setSelectedMethod(e.target.value as 'apollo' | 'google_apify')}
            className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            disabled={isLoading}
          >
            <option value="apollo">Apollo</option>
            <option value="google_apify">Google + Apify</option>
          </select>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.length === 0 ? (
          <div className="text-center py-8">
            <Bot className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Hi! I'm Lead Generation Joe 👋
            </h3>
            <p className="text-gray-600 max-w-md mx-auto">
              I can help you find and generate leads. Just tell me the locations, business types, 
              and job titles you're looking for, and I'll take care of the rest!
            </p>
            <div className="mt-4 p-3 bg-blue-50 rounded-lg max-w-md mx-auto">
              <p className="text-sm text-blue-800">
                <strong>Example:</strong> "Find plant managers in manufacturing companies in New York"
              </p>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {message.role === 'assistant' && (
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                    <Bot className="h-4 w-4 text-primary-600" />
                  </div>
                </div>
              )}
              
              <div className={`max-w-[80%] ${message.role === 'user' ? 'order-1' : ''}`}>
                <div
                  className={`px-4 py-2 rounded-lg ${
                    message.role === 'user'
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                </div>
                <div className={`text-xs text-gray-500 mt-1 ${
                  message.role === 'user' ? 'text-right' : 'text-left'
                }`}>
                  {formatTime(message.timestamp)}
                </div>
              </div>
              
              {message.role === 'user' && (
                <div className="flex-shrink-0 order-2">
                  <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                    <User className="h-4 w-4 text-gray-600" />
                  </div>
                </div>
              )}
            </div>
          ))
        )}
        
        {isLoading && (
          <div className="flex gap-3 justify-start">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                <Bot className="h-4 w-4 text-primary-600" />
              </div>
            </div>
            <div className="bg-gray-100 rounded-lg px-4 py-2">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-gray-600" />
                <span className="text-gray-600">Lead Generation Joe is thinking...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Status Updates Section */}
      {isGeneratingLeads && (
        <div className="p-4 border-t bg-gradient-to-r from-blue-50 to-indigo-50">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-blue-900 flex items-center gap-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
              🚀 Lead Generation in Progress
            </h3>
            <button
              onClick={stopStatusPolling}
              className="text-xs text-blue-600 hover:text-blue-800 px-2 py-1 rounded hover:bg-blue-100 transition-colors"
            >
              Stop
            </button>
          </div>
          <div className="space-y-2 max-h-40 overflow-y-auto bg-white rounded-lg p-3 border border-blue-200">
            {statusUpdates.map((update, index) => {
              const isError = update.includes('❌') || update.includes('⚠️')
              const isSuccess = update.includes('✅')
              const isProgress = !isError && !isSuccess
              
              return (
                <div key={index} className={`text-xs flex items-start gap-2 p-2 rounded ${
                  isError ? 'bg-red-50 text-red-700' : 
                  isSuccess ? 'bg-green-50 text-green-700' : 
                  'bg-blue-50 text-blue-700'
                }`}>
                  <div className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${
                    isError ? 'bg-red-400' : 
                    isSuccess ? 'bg-green-400' : 
                    'bg-blue-400'
                  }`}></div>
                  <div className="font-mono text-xs leading-relaxed break-all">
                    {update}
                  </div>
                </div>
              )
            })}
            {statusUpdates.length === 0 && (
              <div className="text-xs text-blue-600 flex items-center gap-2 p-2">
                <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse"></div>
                <span className="font-mono">Initializing lead generation...</span>
              </div>
            )}
          </div>
          {statusUpdates.length > 0 && (
            <div className="mt-2 text-xs text-blue-600 text-center">
              {statusUpdates.length} status update{statusUpdates.length !== 1 ? 's' : ''}
            </div>
          )}
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Chat with Lead Generation Joe..."
          className="flex-1 input-field"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="btn-primary px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </form>
      
      {/* Quick Actions */}
      {messages.length === 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-sm text-gray-600 mb-2">Quick start examples:</p>
          <div className="flex flex-wrap gap-2">
            {[
              "Find operations managers in manufacturing",
              "Search for plant managers in New York",
              "Look for facility managers in tech companies"
            ].map((example, index) => (
              <button
                key={index}
                onClick={() => setInput(example)}
                className="text-xs px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded-full text-gray-700 transition-colors"
                disabled={isLoading}
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}