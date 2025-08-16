'use client'

import { useState, useEffect } from 'react'
import { Save, RefreshCw, Target, Settings, Users, Building, MapPin, DollarSign, TrendingUp } from 'lucide-react'
import { toast } from 'react-hot-toast'
import apiClient from '@/lib/api-client'

interface ICPCriteria {
  id: string
  name: string
  weight: number
  description: string
  enabled: boolean
}

interface ICPSettings {
  targetIndustries: string[]
  targetJobTitles: string[]
  targetCompanySizes: string[]
  targetLocations: string[]
  excludeIndustries: string[]
  excludeCompanySizes: string[]
  minEmployeeCount: number
  maxEmployeeCount: number
  scoringCriteria: ICPCriteria[]
  customPrompt: string
}

interface ICPStats {
  totalLeads: number
  averageScore: number
  gradeDistribution: {
    'A+': number
    'A': number
    'B+': number
    'B': number
    'C+': number
    'C': number
    'D': number
  }
}

export default function ICPConfigurationPage() {
  const [settings, setSettings] = useState<ICPSettings | null>(null)
  const [stats, setStats] = useState<ICPStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [activeTab, setActiveTab] = useState<'criteria' | 'targeting' | 'prompt' | 'stats'>('criteria')

  useEffect(() => {
    fetchICPSettings()
    fetchICPStats()
  }, [])

  const fetchICPSettings = async () => {
    try {
      const data = await apiClient.getICPSettings()

      if (data.status === 'success') {
        setSettings(data.data)
      } else {
        toast.error(data.message || 'Failed to fetch ICP settings')
      }
    } catch (error) {
      console.error('Error fetching ICP settings:', error)
      toast.error('Error loading ICP settings')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchICPStats = async () => {
    try {
      const data = await apiClient.getICPStats()

      if (data.status === 'success') {
        setStats(data.data)
      } else {
        console.error('Failed to fetch ICP stats:', data.message)
      }
    } catch (error) {
      console.error('Error fetching ICP stats:', error)
    }
  }

  const handleSaveSettings = async () => {
    if (!settings) return

    setIsSaving(true)
    try {
      const data = await apiClient.updateICPSettings(settings)

      if (data.status === 'success') {
        toast.success('✅ ICP settings saved successfully!')
        fetchICPStats() // Refresh stats after saving
      } else {
        toast.error(data.message || 'Failed to save ICP settings')
      }
    } catch (error) {
      console.error('Error saving ICP settings:', error)
      toast.error('Error saving ICP settings')
    } finally {
      setIsSaving(false)
    }
  }

  const handleCriteriaChange = (criteriaId: string, field: keyof ICPCriteria, value: any) => {
    if (!settings) return

    const updatedCriteria = settings.scoringCriteria.map(criteria =>
      criteria.id === criteriaId ? { ...criteria, [field]: value } : criteria
    )

    setSettings({ ...settings, scoringCriteria: updatedCriteria })
  }

  const handleArrayFieldChange = (field: keyof ICPSettings, value: string) => {
    if (!settings) return

    const currentArray = settings[field] as string[]
    const newArray = value.split(',').map(item => item.trim()).filter(item => item.length > 0)
    setSettings({ ...settings, [field]: newArray })
  }

  const getGradeColor = (grade: string) => {
    switch (grade) {
      case 'A+': return 'text-green-600 bg-green-100'
      case 'A': return 'text-green-600 bg-green-100'
      case 'B+': return 'text-blue-600 bg-blue-100'
      case 'B': return 'text-blue-600 bg-blue-100'
      case 'C+': return 'text-yellow-600 bg-yellow-100'
      case 'C': return 'text-yellow-600 bg-yellow-100'
      case 'D': return 'text-red-600 bg-red-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        </div>
      </div>
    )
  }

  if (!settings) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center py-12">
            <p className="text-gray-500">Failed to load ICP settings</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              🎯 ICP Configuration
            </h1>
            <p className="text-gray-600">
              Configure your Ideal Customer Profile scoring criteria and targeting parameters
            </p>
          </div>
          <button
            onClick={handleSaveSettings}
            disabled={isSaving}
            className="btn-primary flex items-center gap-2"
          >
            {isSaving ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Save Settings
          </button>
        </div>

        {/* Tabs */}
        <div className="mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              {[
                { id: 'criteria', label: 'Scoring Criteria', icon: Target },
                { id: 'targeting', label: 'Targeting Rules', icon: Users },
                { id: 'prompt', label: 'Custom Prompt', icon: Settings },
                { id: 'stats', label: 'Statistics', icon: TrendingUp }
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id as any)}
                  className={`flex items-center gap-2 py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === id
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Content */}
        <div className="space-y-6">
          {/* Scoring Criteria Tab */}
          {activeTab === 'criteria' && (
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-6">🎯 Scoring Criteria</h3>
              <div className="space-y-6">
                {settings.scoringCriteria.map((criteria) => (
                  <div key={criteria.id} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <input
                          type="checkbox"
                          checked={criteria.enabled}
                          onChange={(e) => handleCriteriaChange(criteria.id, 'enabled', e.target.checked)}
                          className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                        />
                        <h4 className="text-lg font-medium text-gray-900">{criteria.name}</h4>
                      </div>
                      <div className="flex items-center gap-2">
                        <label className="text-sm font-medium text-gray-700">Weight:</label>
                        <input
                          type="number"
                          min="0"
                          max="100"
                          value={criteria.weight}
                          onChange={(e) => handleCriteriaChange(criteria.id, 'weight', parseInt(e.target.value))}
                          className="w-20 input-field"
                        />
                        <span className="text-sm text-gray-500">%</span>
                      </div>
                    </div>
                    <p className="text-gray-600 mb-4">{criteria.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Targeting Rules Tab */}
          {activeTab === 'targeting' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Target Industries */}
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <Building className="h-5 w-5" />
                  Target Industries
                </h3>
                <textarea
                  value={settings.targetIndustries.join(', ')}
                  onChange={(e) => handleArrayFieldChange('targetIndustries', e.target.value)}
                  rows={4}
                  className="input-field resize-none"
                  placeholder="Manufacturing, Healthcare, Technology, etc."
                />
                <p className="text-sm text-gray-500 mt-2">Separate industries with commas</p>
              </div>

              {/* Target Job Titles */}
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  Target Job Titles
                </h3>
                <textarea
                  value={settings.targetJobTitles.join(', ')}
                  onChange={(e) => handleArrayFieldChange('targetJobTitles', e.target.value)}
                  rows={4}
                  className="input-field resize-none"
                  placeholder="Operations Manager, Facility Manager, Plant Manager, etc."
                />
                <p className="text-sm text-gray-500 mt-2">Separate job titles with commas</p>
              </div>

              {/* Target Company Sizes */}
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <DollarSign className="h-5 w-5" />
                  Target Company Sizes
                </h3>
                <textarea
                  value={settings.targetCompanySizes.join(', ')}
                  onChange={(e) => handleArrayFieldChange('targetCompanySizes', e.target.value)}
                  rows={3}
                  className="input-field resize-none"
                  placeholder="Small, Medium, Large, Enterprise"
                />
                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Min Employees</label>
                    <input
                      type="number"
                      value={settings.minEmployeeCount}
                      onChange={(e) => setSettings({ ...settings, minEmployeeCount: parseInt(e.target.value) || 0 })}
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Max Employees</label>
                    <input
                      type="number"
                      value={settings.maxEmployeeCount}
                      onChange={(e) => setSettings({ ...settings, maxEmployeeCount: parseInt(e.target.value) || 0 })}
                      className="input-field"
                    />
                  </div>
                </div>
              </div>

              {/* Target Locations */}
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <MapPin className="h-5 w-5" />
                  Target Locations
                </h3>
                <textarea
                  value={settings.targetLocations.join(', ')}
                  onChange={(e) => handleArrayFieldChange('targetLocations', e.target.value)}
                  rows={3}
                  className="input-field resize-none"
                  placeholder="United States, Canada, Europe, etc."
                />
                <p className="text-sm text-gray-500 mt-2">Separate locations with commas</p>
              </div>
            </div>
          )}

          {/* Custom Prompt Tab */}
          {activeTab === 'prompt' && (
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Custom ICP Scoring Prompt
              </h3>
              <p className="text-gray-600 mb-4">
                Customize the AI prompt used for ICP scoring. Use placeholders like {'{profile}'} for lead data.
              </p>
              <textarea
                value={settings.customPrompt}
                onChange={(e) => setSettings({ ...settings, customPrompt: e.target.value })}
                rows={12}
                className="input-field resize-none font-mono text-sm"
                placeholder="Enter your custom ICP scoring prompt here..."
              />
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h4 className="font-medium text-blue-900 mb-2">Available Placeholders:</h4>
                <div className="grid grid-cols-2 gap-2 text-sm text-blue-800">
                  <span>• {'{profile}'} - Complete lead profile</span>
                  <span>• {'{fullName}'} - Lead's full name</span>
                  <span>• {'{jobTitle}'} - Lead's job title</span>
                  <span>• {'{companyName}'} - Company name</span>
                  <span>• {'{industry}'} - Company industry</span>
                  <span>• {'{location}'} - Lead's location</span>
                </div>
              </div>
            </div>
          )}

          {/* Statistics Tab */}
          {activeTab === 'stats' && stats && (
            <div className="space-y-6">
              {/* Overview Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="card text-center">
                  <Users className="h-8 w-8 text-blue-500 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-gray-900">{stats.totalLeads.toLocaleString()}</p>
                  <p className="text-sm text-gray-600">Total Scored Leads</p>
                </div>
                <div className="card text-center">
                  <Target className="h-8 w-8 text-green-500 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-gray-900">{stats.averageScore.toFixed(1)}</p>
                  <p className="text-sm text-gray-600">Average ICP Score</p>
                </div>
                <div className="card text-center">
                  <TrendingUp className="h-8 w-8 text-purple-500 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-gray-900">
                    {((stats.gradeDistribution['A+'] + stats.gradeDistribution['A']) / stats.totalLeads * 100).toFixed(1)}%
                  </p>
                  <p className="text-sm text-gray-600">High-Quality Leads</p>
                </div>
              </div>

              {/* Grade Distribution */}
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-6">📊 Grade Distribution</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
                  {Object.entries(stats.gradeDistribution).map(([grade, count]) => (
                    <div key={grade} className="text-center">
                      <div className={`inline-flex items-center justify-center w-12 h-12 rounded-full font-bold text-lg mb-2 ${getGradeColor(grade)}`}>
                        {grade}
                      </div>
                      <p className="text-xl font-semibold text-gray-900">{count}</p>
                      <p className="text-sm text-gray-600">
                        {stats.totalLeads > 0 ? ((count / stats.totalLeads) * 100).toFixed(1) : 0}%
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}