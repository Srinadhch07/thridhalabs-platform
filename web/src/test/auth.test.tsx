/** AuthProvider tests — session bootstrap from the HttpOnly cookie. */

import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AuthProvider, useAuth, type AuthStatus } from '../app/providers/AuthProvider'
import { installFetchMock } from './helpers'
import type { Me } from '../types/admin'

function AuthProbe() {
  const { status, user, error } = useAuth()
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="user">{user?.email ?? 'none'}</span>
      <span data-testid="error">{error ? 'yes' : 'no'}</span>
    </div>
  )
}

interface SignOutProbe {
  register: (probe: { signOut: () => Promise<void> }) => void
}

function AuthProbeSnapshot({ register }: SignOutProbe) {
  const { signOut } = useAuth()
  register({ signOut })
  return null
}

function renderAuth() {
  return render(
    <AuthProvider>
      <AuthProbe />
    </AuthProvider>,
  )
}

function expectEventually(status: AuthStatus, email = 'none', error = 'no') {
  return waitFor(() => {
    expect(screen.getByTestId('status').textContent).toBe(status)
    expect(screen.getByTestId('user').textContent).toBe(email)
    expect(screen.getByTestId('error').textContent).toBe(error)
  })
}

const me: Me = { id: 'u-1', email: 'owner@thridhalabs.com', role: 'owner', is_active: true }

describe('AuthProvider', () => {
  it('starts in the loading state', () => {
    installFetchMock({ '/api/auth/me': { body: me } })
    renderAuth()
    expect(screen.getByTestId('status').textContent).toBe('loading')
  })

  it('becomes authenticated when /auth/me returns a session', async () => {
    installFetchMock({ '/api/auth/me': { body: me } })
    renderAuth()
    await expectEventually('authenticated', me.email)
  })

  it('becomes unauthenticated without an error on 401', async () => {
    installFetchMock({
      '/api/auth/me': { status: 401, body: { error: { code: 'NOT_AUTHENTICATED', message: 'no session' } } },
    })
    renderAuth()
    await expectEventually('unauthenticated')
  })

  it('becomes unauthenticated with an error for a non-401 failure', async () => {
    installFetchMock({ '/api/auth/me': { status: 503, body: { error: { code: 'DB', message: 'down' } } } })
    renderAuth()
    await expectEventually('unauthenticated', 'none', 'yes')
  })

  it('never stores the session token in web storage', async () => {
    installFetchMock({ '/api/auth/me': { body: me } })
    renderAuth()
    await expectEventually('authenticated', me.email)
    expect(sessionStorage.length).toBe(0)
    expect(localStorage.length).toBe(0)
  })

  it('signOut posts /auth/logout and returns to unauthenticated', async () => {
    const { calls } = installFetchMock({
      '/api/auth/me': { body: me },
      '/api/auth/csrf': { body: { csrfToken: 't' } },
      '/api/auth/logout': { status: 200, body: { status: 'ok' } },
    })
    let signOut!: () => Promise<void>
    render(
      <AuthProvider>
        <AuthProbe />
        <AuthProbeSnapshot register={(p) => (signOut = p.signOut)} />
      </AuthProvider>,
    )

    await expectEventually('authenticated', me.email)
    await signOut()
    expect(calls.some((c) => c.url.includes('/api/auth/logout'))).toBe(true)
    await expectEventually('unauthenticated')
  })
})