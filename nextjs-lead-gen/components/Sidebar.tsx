'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

import { 
  Target, 
  Database, 
  Mail, 
  BarChart3, 
  Settings, 
  ChevronLeft,
  ChevronRight,
  User
} from 'lucide-react'
import { clsx } from 'clsx'
import toast from 'react-hot-toast'

const navigation = [
  {
    name: 'Lead Generation',
    href: '/generate',
    icon: Target,
    description: 'Generate new leads'
  },
  {
    name: 'Leads Database',
    href: '/leads',
    icon: Database,
    description: 'View and manage leads'
  },
  {
    name: 'Email Management',
    href: '/email',
    icon: Mail,
    description: 'Send and track emails'
  },
  {
    name: 'Email Dashboard',
    href: '/dashboard',
    icon: BarChart3,
    description: 'Email analytics'
  },
  {
    name: 'ICP Configuration',
    href: '/icp',
    icon: Settings,
    description: 'Configure ICP settings'
  },
]

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const pathname = usePathname()


  return (
    <div className={clsx(
      'bg-gradient-to-b from-white via-primary-50/30 to-accent-50/50 backdrop-blur-xl border-r border-primary-200/50 shadow-xl transition-all duration-300 flex flex-col',
      collapsed ? 'w-16' : 'w-64'
    )}>
      {/* Header */}
      <div className="p-6 border-b border-primary-200/30">
        <div className="flex items-center justify-between">
          {!collapsed && (
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-brand-500 to-brand-600 rounded-xl shadow-lg">
                <Target className="h-6 w-6 text-white" />
              </div>
              <span className="font-bold text-primary-900 text-lg">Lead Gen</span>
            </div>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-2 rounded-xl hover:bg-primary-100/50 transition-all duration-200 hover:shadow-md"
          >
            {collapsed ? (
              <ChevronRight className="h-5 w-5 text-primary-600" />
            ) : (
              <ChevronLeft className="h-5 w-5 text-primary-600" />
            )}
          </button>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-6">
        <div className="space-y-3">
          {navigation.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.name}
                href={item.href}
                className={clsx(
                  'flex items-center gap-4 px-4 py-3 rounded-2xl transition-all duration-300 group relative overflow-hidden',
                  isActive
                    ? 'bg-gradient-to-r from-brand-500 to-brand-600 text-white shadow-lg transform scale-105'
                    : 'text-primary-700 hover:bg-gradient-to-r hover:from-primary-100 hover:to-accent-100 hover:text-primary-900 hover:shadow-md hover:scale-105'
                )}
                title={collapsed ? item.name : undefined}
              >
                <div className={clsx(
                  'p-2 rounded-xl transition-all duration-300',
                  isActive 
                    ? 'bg-white/20 shadow-inner' 
                    : 'bg-primary-100/50 group-hover:bg-white/80 group-hover:shadow-md'
                )}>
                  <item.icon className={clsx(
                    'h-5 w-5 flex-shrink-0 transition-all duration-300',
                    isActive ? 'text-white' : 'text-brand-600 group-hover:text-brand-700'
                  )} />
                </div>
                {!collapsed && (
                  <div className="flex-1 min-w-0">
                    <div className={clsx(
                      'font-semibold text-sm transition-colors duration-300',
                      isActive ? 'text-white' : 'text-primary-900'
                    )}>{item.name}</div>
                    <div className={clsx(
                      'text-xs truncate transition-colors duration-300',
                      isActive ? 'text-white/80' : 'text-primary-600'
                    )}>
                      {item.description}
                    </div>
                  </div>
                )}
              </Link>
            )
          })}
        </div>
      </nav>

      {/* User Section */}
      <div className="p-6 border-t border-primary-200/30">
        {!collapsed && (
          <div className="flex items-center gap-4 px-4 py-3 bg-gradient-to-r from-primary-50 to-accent-50 rounded-2xl border border-primary-200/50 shadow-sm">
            <div className="h-10 w-10 bg-gradient-to-br from-brand-500 to-brand-600 rounded-xl flex items-center justify-center shadow-md">
              <User className="h-5 w-5 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-primary-900 truncate">
                Lead Gen User
              </p>
              <p className="text-xs text-brand-600 font-medium">● Active</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}