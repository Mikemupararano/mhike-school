'use client'

import { ReactNode, useEffect } from 'react'
import { useRouter } from 'next/navigation'

import { UserRole } from '@/types/user'
import { useAuth } from '@/hooks/useAuth'

type RoleGateProps = {
  allowedRoles: UserRole[]
  children: ReactNode
  fallback?: ReactNode
  redirectTo?: string // ✅ optional improvement
}

export default function RoleGate({
  allowedRoles,
  children,
  fallback = null,
  redirectTo = '/login',
}: RoleGateProps) {
  const { user, isLoading } = useAuth()
  const router = useRouter()

  // ✅ Handle redirect safely (no side-effects in render)
  useEffect(() => {
    if (!isLoading && !user) {
      router.replace(redirectTo)
    }
  }, [user, isLoading, router, redirectTo])

  // ⏳ Loading state
  if (isLoading) {
    return <div className="p-4">Loading...</div>
  }

  // 🚫 Not logged in (while redirecting)
  if (!user) {
    return null
  }

  // 🔒 Role check
  if (!allowedRoles.includes(user.role)) {
    return (
      fallback ?? (
        <div className="p-4 text-red-500">
          You do not have permission to access this page.
        </div>
      )
    )
  }

  // ✅ Allowed
  return <>{children}</>
}