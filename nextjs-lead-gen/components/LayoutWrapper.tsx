'use client'

import { usePathname } from 'next/navigation'
import Sidebar from '@/components/Sidebar'

interface LayoutWrapperProps {
  children: React.ReactNode
}

export default function LayoutWrapper({ children }: LayoutWrapperProps) {
  const pathname = usePathname()
  
  // Show sidebar for all routes except home page
  if (pathname === '/') {
    return <>{children}</>
  }

  return (
    <div className="flex h-screen bg-gradient-to-br from-primary-50/30 via-white to-accent-50/30">
      <Sidebar />
      <main className="flex-1 overflow-auto bg-gradient-to-br from-white/50 to-primary-50/20 backdrop-blur-sm">
        <div className="min-h-full p-6">
          {children}
        </div>
      </main>
    </div>
  )
}