/**
 * MemberAuthProvider — session foundation for the member portal.
 *
 * Mirrors `AuthProvider` but for member accounts: the HttpOnly session cookie
 * stays the source of truth and `GET /api/member/me` resolves the current state.
 * Mounted only around the `/member/*` route subtree so public and admin pages
 * are unaffected by an extra probe request.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { getMemberMe, memberLogout } from '../../features/members/api'
import { isApiError } from '../../lib/errors/ApiError'
import type { MemberMe } from '../../types/member'

export type MemberAuthStatus = 'loading' | 'authenticated' | 'unauthenticated'

interface MemberAuthContextValue {
  status: MemberAuthStatus
  member: MemberMe | null
  error: Error | null
  refresh: () => Promise<void>
  signOut: () => Promise<void>
}

const MemberAuthContext = createContext<MemberAuthContextValue | null>(null)

export function MemberAuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<MemberAuthStatus>('loading')
  const [member, setMember] = useState<MemberMe | null>(null)
  const [error, setError] = useState<Error | null>(null)

  const refresh = useCallback(async () => {
    setStatus('loading')
    setError(null)
    try {
      const me = await getMemberMe()
      setMember(me)
      setStatus('authenticated')
    } catch (caught) {
      setMember(null)
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
      await memberLogout()
    } catch {
      // Session may already be gone — sign out locally regardless.
    }
    setMember(null)
    setStatus('unauthenticated')
  }, [])

  const value = useMemo(
    () => ({ status, member, error, refresh, signOut }),
    [status, member, error, refresh, signOut],
  )

  return <MemberAuthContext.Provider value={value}>{children}</MemberAuthContext.Provider>
}

export function useMemberAuth(): MemberAuthContextValue {
  const context = useContext(MemberAuthContext)
  if (!context) {
    throw new Error('useMemberAuth must be used within a <MemberAuthProvider>')
  }
  return context
}