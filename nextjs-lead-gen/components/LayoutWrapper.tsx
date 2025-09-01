'use client'

import { usePathname } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import Sidebar from '@/components/Sidebar'
import AuthGuard from '@/components/AuthGuard'

interface LayoutWrapperProps {
  children: React.ReactNode
}

export default function LayoutWrapper({ children }: LayoutWrapperProps) {
  const pathname = usePathname()
  const { user } = useAuth()
  
  // Public routes that don't require authentication
  const publicRoutes = ['/login', '/signup', '/auth']
  const isPublicRoute = publicRoutes.some(route => pathname.startsWith(route))
  
  // For public routes, render without sidebar
  if (isPublicRoute) {
    return <>{children}</>
  }

  // For protected routes, require authentication and show sidebar
  return (
    <AuthGuard requireAuth={true}>
      <div className="flex h-screen bg-gradient-to-br from-primary-50/30 via-white to-accent-50/30">
        <Sidebar />
        <main className="flex-1 overflow-auto bg-gradient-to-br from-white/50 to-primary-50/20 backdrop-blur-sm">
          <div className="min-h-full p-6">
            {children}
          </div>
        </main>
      </div>
    </AuthGuard>
  )
}