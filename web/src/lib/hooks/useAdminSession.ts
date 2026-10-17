/**
 * useAdminSession — admin-side session handling.
 *
 * When an authenticated data call surfaces a 401 (expired/revoked session),
 * the frontend auth state is cleared and the user is routed back to
 * /admin/login with the current page preserved as the return destination.
 */

import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../app/providers/AuthProvider'
import { isApiError } from '../errors/ApiError'

export function useAdminSessionIssue(error: Error | null | undefined): void {
  const { signOut } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    if (!error) return
    if (!isApiError(error)) return
    if (error.status !== 401) return
    void signOut().then(() => {
      navigate('/admin/login', {
        replace: true,
        state: { from: location.pathname },
      })
    })
  }, [error, signOut, navigate, location.pathname])
}