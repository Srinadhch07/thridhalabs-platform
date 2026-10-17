/**
 * useMemberSession — member-side session handling.
 *
 * When an authenticated data call surfaces a 401 (expired/revoked session),
 * the member auth state is cleared and the member is routed back to
 * /member/login with the current page preserved as the return destination.
 */

import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useMemberAuth } from '../../app/providers/MemberAuthProvider'
import { isApiError } from '../errors/ApiError'

export function useMemberSessionIssue(error: Error | null | undefined): void {
  const { signOut } = useMemberAuth()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    if (!error) return
    if (!isApiError(error)) return
    if (error.status !== 401) return
    void signOut().then(() => {
      navigate('/member/login', {
        replace: true,
        state: { from: location.pathname },
      })
    })
  }, [error, signOut, navigate, location.pathname])
}