/**
 * AuthProvider — frontend session foundation.
 *
 * The HttpOnly session cookie is the single source of truth; `/auth/me`
 * determines the current state. No JWT is ever stored in localStorage or
 * sessionStorage.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { getMe, logout } from '../../features/auth/api'
import { isApiError } from '../../lib/errors/ApiError'
import type { Me } from '../../types/admin'

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated'

interface AuthContextValue {
  status: AuthStatus
  user: Me | null
  error: Error | null
  refresh: () => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUser] = useState<Me | null>(null)
  const [error, setError] = useState<Error | null>(null)

  const refresh = useCallback(async () => {
    setStatus('loading')
    setError(null)
    try {
      const me = await getMe()
      setUser(me)
      setStatus('authenticated')
    } catch (caught) {
      setUser(null)
      setStatus('unauthenticated')
      if (!(isApiError(caught) && caught.status === 401)) {
        setError(caught instanceof Error ? caught : new Error(String(caught)))
      }
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const signOut = useCallback(async () => {
    try {
      await logout()
    } catch {
      // Session may already be gone — sign out locally regardless.
    }
    setUser(null)
    setStatus('unauthenticated')
  }, [])

  const value = useMemo(
    () => ({ status, user, error, refresh, signOut }),
    [status, user, error, refresh, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an <AuthProvider>')
  }
  return context
}