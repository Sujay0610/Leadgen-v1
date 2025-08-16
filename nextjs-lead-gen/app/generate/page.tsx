'use client'

import { useState, useEffect } from 'react'
import { Target, Zap, Database, Mail, Settings, Search, Bot } from 'lucide-react'
import LeadGenerationForm from '@/components/LeadGenerationForm'
import ChatInterface from '@/components/ChatInterface'
import APIStatus from '@/components/APIStatus'
import LeadMetrics from '@/components/LeadMetrics'
import { toast } from 'react-hot-toast'

export default function GenerateLeadsPage() {
  const [inputMethod, setInputMethod] = useState<'form' | 'chat'>('form')
  const [leadsPerQuery, setLeadsPerQuery] = useState(20)
  const [isLoading, setIsLoading] = useState(false)

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <Target className="h-8 w-8 text-primary-600" />
          <h1 className="text-3xl font-bold text-gray-900">
            Lead Generation System
          </h1>
        </div>
        <p className="text-gray-600 text-lg">
          Powered by AI Agent + Web Scraping + Data Enrichment + ICP Scoring
        </p>
      </div>

      {/* Input Method Toggle */}
      <div className="mb-6">
        <div className="flex items-center gap-4 p-1 bg-gray-100 rounded-lg w-fit">
          <button
            onClick={(e) => {
              e.preventDefault()
              setInputMethod('form')
            }}
            className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
              inputMethod === 'form'
                ? 'bg-white text-primary-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Search className="h-4 w-4" />
            <span className="text-base font-medium">Direct Query Form</span>
          </button>
          <button
            onClick={(e) => {
              e.preventDefault()
              setInputMethod('chat')
            }}
            className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
              inputMethod === 'chat'
                ? 'bg-white text-primary-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Bot className="h-4 w-4" />
            Chat with Lead Generation Joe
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-3">
          {inputMethod === 'form' ? (
            <LeadGenerationForm 
              leadsPerQuery={leadsPerQuery}
              onLeadsGenerated={() => {
                toast.success('Leads generated successfully!')
              }}
            />
          ) : (
            <ChatInterface />
          )}
        </div>

        {/* Sidebar */}
        <div className="lg:col-span-1 space-y-6">
          {/* Configuration */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Configuration
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  🎯 Leads per search query
                </label>
                <select
                  value={leadsPerQuery}
                  onChange={(e) => setLeadsPerQuery(Number(e.target.value))}
                  className="input-field"
                >
                  <option value={1}>1</option>
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  More leads = longer processing time
                </p>
              </div>
            </div>
          </div>

          {/* API Status */}
          <APIStatus />

          {/* ICP Scoring Info */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Zap className="h-5 w-5" />
              ICP Scoring
            </h3>
            <div className="text-sm text-gray-600 space-y-2">
              <p className="font-medium">Scoring Criteria:</p>
              <ul className="space-y-1">
                <li>• Job Title Match (0-10 points)</li>
                <li>• Company Size (0-10 points)</li>
                <li>• Industry (0-10 points)</li>
                <li>• Location (0-10 points)</li>
              </ul>
              <p className="font-medium mt-3">Total: 0-40 points (converted to %)</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}