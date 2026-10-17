/**
 * Admin route boundary — guarantees admin routes can never accidentally render
 * through the public application assumptions (or vice versa).
 */

import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'

export function AdminRouteBoundary({ children }: { children: ReactNode }) {
  const location = useLocation()
  if (!location.pathname.startsWith('/admin')) {
    return <Navigate to="/404" replace />
  }
  return <>{children}</>
}