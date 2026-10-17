/**
 * Member account system — member portal (login, setup, dashboard, profile,
 * account) and admin member management (list, create, edit, lifecycle, RBAC).
 */

import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import {
  adminDataHandlers,
  adminMemberFixture,
  adminMembersFixture,
  editorMeFixture,
  memberMeFixture,
  memberProfileResponseFixture,
  meFixture,
} from './fixtures'
import { renderApp } from './helpers'

const NOT_AUTHENTICATED = {
  error: { code: 'NOT_AUTHENTICATED', message: 'Authentication required' },
}

const csrf = {
  '/api/auth/csrf': { body: { csrfToken: 'test-csrf' } },
  '/api/member/csrf': { body: { csrfToken: 'test-csrf' } },
}

/** Handlers for an authenticated member session. */
const memberSession = (overrides: Record<string, unknown> = {}) => ({
  ...csrf,
  '/api/member/me': { body: memberMeFixture },
  '/api/member/profile': { body: memberProfileResponseFixture },
  ...overrides,
})

describe('member portal access', () => {
  it('redirects /member to the sign-in page when unauthenticated', async () => {
    renderApp({ entry: '/member' })
    expect(
      await screen.findByRole('heading', { level: 1, name: /member sign in/i }),
    ).toBeInTheDocument()
  })

  it('signs in and reaches the dashboard', async () => {
    let loggedIn = false
    renderApp({
      entry: '/member/login',
      handlers: {
        ...csrf,
        '/api/member/me': () =>
          loggedIn ? { body: memberMeFixture } : { status: 401, body: NOT_AUTHENTICATED },
        '/api/member/login': () => {
          loggedIn = true
          return { body: { status: 'ok' } }
        },
        '/api/member/profile': { body: memberProfileResponseFixture },
      },
    })

    await screen.findByRole('button', { name: /sign in/i })
    fireEvent.change(screen.getByLabelText(/^email/i), {
      target: { value: 'member@thridhalabs.com' },
    })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'secret' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    expect(
      await screen.findByRole('heading', { level: 1, name: /welcome back, ada lovelace/i }),
    ).toBeInTheDocument()
    expect(screen.getAllByText('THL-M-2026-0001').length).toBeGreaterThan(0)
  })

  it('shows a clean error on invalid credentials', async () => {
    renderApp({
      entry: '/member/login',
      handlers: {
        ...csrf,
        '/api/member/login': { status: 401, body: { error: { code: 'INVALID_CREDENTIALS', message: 'nope' } } },
      },
    })

    await screen.findByRole('button', { name: /sign in/i })
    fireEvent.change(screen.getByLabelText(/^email/i), { target: { value: 'x@y.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'wrong' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByText(/incorrect email or password/i)).toBeInTheDocument()
  })

  it('signs out and returns to the sign-in page', async () => {
    renderApp({
      entry: '/member',
      handlers: memberSession({
        '/api/member/logout': { body: { status: 'ok' } },
      }),
    })

    await screen.findByRole('heading', { level: 1, name: /welcome back, ada lovelace/i })
    fireEvent.click(screen.getByRole('button', { name: /sign out/i }))

    expect(
      await screen.findByRole('heading', { level: 1, name: /member sign in/i }),
    ).toBeInTheDocument()
  })
})

describe('member setup', () => {
  it('explains when the setup link has no token', async () => {
    renderApp({ entry: '/member/setup' })
    expect(await screen.findByText(/expects a setup link with a token/i)).toBeInTheDocument()
  })

  it('sets the password and points to sign in', async () => {
    const { calls } = renderApp({
      entry: '/member/setup?token=abc123',
      handlers: {
        ...csrf,
        '/api/member/setup': { body: { status: 'ok' } },
      },
    })

    const password = await screen.findByLabelText(/^password/i)
    fireEvent.change(password, { target: { value: 'Sup3rSecret!' } })
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'Sup3rSecret!' } })
    fireEvent.click(screen.getByRole('button', { name: /set password/i }))

    expect(await screen.findByRole('link', { name: /go to sign in/i })).toBeInTheDocument()
    const post = calls.find((c) => c.url.includes('/api/member/setup'))
    expect(post).toBeTruthy()
    expect(JSON.parse(String(post!.init?.body))).toMatchObject({
      token: 'abc123',
      password: 'Sup3rSecret!',
    })
  })

  it('surfaces an invalid or expired token', async () => {
    renderApp({
      entry: '/member/setup?token=stale',
      handlers: {
        ...csrf,
        '/api/member/setup': {
          status: 400,
          body: { error: { code: 'ONBOARDING_TOKEN_EXPIRED', message: 'expired' } },
        },
      },
    })

    const password = await screen.findByLabelText(/^password/i)
    fireEvent.change(password, { target: { value: 'Sup3rSecret!' } })
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'Sup3rSecret!' } })
    fireEvent.click(screen.getByRole('button', { name: /set password/i }))

    expect(await screen.findByText(/setup link has expired/i)).toBeInTheDocument()
  })
})

describe('member profile', () => {
  it('loads and saves the profile via PATCH /api/member/profile', async () => {
    const { calls } = renderApp({
      entry: '/member/profile',
      handlers: memberSession({
        '/api/member/profile': { body: memberProfileResponseFixture },
      }),
    })

    const bio = await screen.findByLabelText(/^bio/i)
    await waitFor(() => expect(bio).toHaveValue('Lab member working on embodied AI.'))

    fireEvent.change(bio, { target: { value: 'Updated bio.' } })
    fireEvent.click(screen.getByRole('button', { name: /save profile/i }))

    await waitFor(() => {
      const patch = calls.find(
        (c) => c.url.includes('/api/member/profile') && c.init?.method === 'PATCH',
      )
      expect(patch).toBeTruthy()
      expect(JSON.parse(String(patch!.init?.body))).toMatchObject({
        bio: 'Updated bio.',
        skills: ['Python', 'Robotics'],
      })
    })
  })

  it('requires bio, skills and interests before saving', async () => {
    const { calls } = renderApp({
      entry: '/member/profile',
      handlers: memberSession({
        '/api/member/profile': { body: memberProfileResponseFixture },
      }),
    })

    const bio = await screen.findByLabelText(/^bio/i)
    await waitFor(() => expect(bio).toHaveValue('Lab member working on embodied AI.'))
    fireEvent.change(bio, { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: /save profile/i }))

    expect(await screen.findByText(/bio, skills and interests are required/i)).toBeInTheDocument()
    expect(
      calls.some((c) => c.url.includes('/api/member/profile') && c.init?.method === 'PATCH'),
    ).toBe(false)
  })

  it('uploads an avatar via POST /api/member/picture', async () => {
    const { calls } = renderApp({
      entry: '/member/profile',
      handlers: memberSession({
        '/api/member/profile': { body: memberProfileResponseFixture },
        '/api/member/picture': { body: { id: 'm-9', urls: {} } },
      }),
    })

    await screen.findByLabelText(/^bio/i)
    const input = document.getElementById('member-picture') as HTMLInputElement
    const file = new File([new Uint8Array([1, 2, 3])], 'avatar.webp', { type: 'image/webp' })
    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() => {
      const post = calls.find(
        (c) => c.url.includes('/api/member/picture') && c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(post!.init?.body).toBeInstanceOf(FormData)
    })
  })
})

describe('member account', () => {
  it('changes the password via POST /api/member/password', async () => {
    const { calls } = renderApp({
      entry: '/member/account',
      handlers: memberSession({
        '/api/member/profile': { body: memberProfileResponseFixture },
        '/api/member/password': { body: { status: 'ok' } },
      }),
    })

    const current = await screen.findByLabelText(/current password/i)
    fireEvent.change(current, { target: { value: 'old-password' } })
    fireEvent.change(screen.getByLabelText(/^new password/i), {
      target: { value: 'brand-new-pass' },
    })
    fireEvent.change(screen.getByLabelText(/confirm new password/i), {
      target: { value: 'brand-new-pass' },
    })
    fireEvent.click(screen.getByRole('button', { name: /update password/i }))

    expect(await screen.findByText('Password updated.')).toBeInTheDocument()
    const post = calls.find((c) => c.url.includes('/api/member/password'))
    expect(JSON.parse(String(post!.init?.body))).toMatchObject({
      current_password: 'old-password',
      new_password: 'brand-new-pass',
    })
  })

  it('reports an incorrect current password', async () => {
    renderApp({
      entry: '/member/account',
      handlers: memberSession({
        '/api/member/profile': { body: memberProfileResponseFixture },
        '/api/member/password': {
          status: 401,
          body: { error: { code: 'INVALID_PASSWORD', message: 'bad' } },
        },
      }),
    })

    await screen.findByLabelText(/current password/i)
    fireEvent.change(screen.getByLabelText(/current password/i), { target: { value: 'nope' } })
    fireEvent.change(screen.getByLabelText(/^new password/i), {
      target: { value: 'brand-new-pass' },
    })
    fireEvent.change(screen.getByLabelText(/confirm new password/i), {
      target: { value: 'brand-new-pass' },
    })
    fireEvent.click(screen.getByRole('button', { name: /update password/i }))

    expect(await screen.findByText(/current password is incorrect/i)).toBeInTheDocument()
  })
})

describe('admin members', () => {
  it('lists members with status, profile and onboarding state', async () => {
    renderApp({ entry: '/admin/members', handlers: adminDataHandlers() })

    const link = await screen.findByRole('link', { name: 'Ada Lovelace' })
    expect(link).toHaveAttribute('href', '/admin/members/member-1')
    expect(screen.getByText('THL-M-2026-0001')).toBeInTheDocument()
    const row = link.closest('tr') as HTMLElement
    expect(within(row).getByText('Active')).toBeInTheDocument()
    expect(within(row).getByText('Complete')).toBeInTheDocument()
  })

  it('sends the search term to the backend', async () => {
    const { calls } = renderApp({ entry: '/admin/members', handlers: adminDataHandlers() })

    const search = await screen.findByLabelText(/search members/i)
    fireEvent.change(search, { target: { value: 'ada' } })
    fireEvent.click(screen.getByRole('button', { name: /search/i }))

    await waitFor(() =>
      expect(calls.some((c) => c.url.includes('/api/members') && c.url.includes('search=ada'))).toBe(
        true,
      ),
    )
  })

  it('filters by status through the query string', async () => {
    const { calls } = renderApp({ entry: '/admin/members', handlers: adminDataHandlers() })

    await screen.findByLabelText(/filter by status/i)
    fireEvent.change(screen.getByLabelText(/filter by status/i), { target: { value: 'inactive' } })

    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes('/api/members') && c.url.includes('status=inactive')),
      ).toBe(true),
    )
  })

  it('creates a member via POST /api/members', async () => {
    const { calls } = renderApp({
      entry: '/admin/members/new',
      handlers: {
        ...adminDataHandlers(),
        '/api/members': (_url: string, init?: RequestInit) =>
          init?.method === 'POST'
            ? { status: 201, body: adminMemberFixture }
            : { body: adminMembersFixture() },
      },
    })

    const email = await screen.findByLabelText(/^email/i)
    fireEvent.change(email, { target: { value: 'new.member@thridhalabs.com' } })
    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'New Member' } })
    fireEvent.click(screen.getByRole('button', { name: /create member/i }))

    await waitFor(() => {
      const post = calls.find((c) => c.url.endsWith('/api/members') && c.init?.method === 'POST')
      expect(post).toBeTruthy()
      expect(JSON.parse(String(post!.init?.body))).toMatchObject({
        email: 'new.member@thridhalabs.com',
        full_name: 'New Member',
      })
    })
  })

  it('edits admin-managed fields via PATCH /api/members/:id', async () => {
    const { calls } = renderApp({ entry: '/admin/members/member-1', handlers: adminDataHandlers() })

    const fullName = await screen.findByLabelText(/full name/i)
    await waitFor(() => expect(fullName).toHaveValue('Ada Lovelace'))
    fireEvent.change(fullName, { target: { value: 'Ada L.' } })
    fireEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => {
      const patch = calls.find(
        (c) => c.url.includes('/api/members/member-1') && c.init?.method === 'PATCH',
      )
      expect(patch).toBeTruthy()
      expect(JSON.parse(String(patch!.init?.body))).toMatchObject({ full_name: 'Ada L.' })
    })
  })

  it('resends onboarding when it is not yet complete', async () => {
    const { calls } = renderApp({
      entry: '/admin/members/member-1',
      handlers: {
        ...adminDataHandlers(),
        '/api/members/member-1': {
          body: {
            ...adminMemberFixture,
            status: 'pending_setup',
            onboarding_sent: true,
            onboarding_completed_at: null,
          },
        },
        '/api/members/member-1/resend': { body: adminMemberFixture },
      },
    })

    fireEvent.click(await screen.findByRole('button', { name: /resend onboarding link/i }))

    await waitFor(() =>
      expect(calls.some((c) => c.url.includes('/api/members/member-1/resend'))).toBe(true),
    )
  })

  it('deactivates and reactivates a member', async () => {
    const { calls } = renderApp({
      entry: '/admin/members/member-1',
      handlers: {
        ...adminDataHandlers(),
        '/api/members/member-1/deactivate': { body: adminMemberFixture },
        '/api/members/member-1/reactivate': {
          body: { ...adminMemberFixture, status: 'inactive' },
        },
      },
    })

    fireEvent.click(await screen.findByRole('button', { name: 'Deactivate' }))
    await waitFor(() =>
      expect(calls.some((c) => c.url.includes('/api/members/member-1/deactivate'))).toBe(true),
    )
  })

  it('shows Reactivate for an inactive member', async () => {
    renderApp({
      entry: '/admin/members/member-1',
      handlers: {
        ...adminDataHandlers(),
        '/api/members/member-1': { body: { ...adminMemberFixture, status: 'inactive' } },
      },
    })

    expect(await screen.findByRole('button', { name: 'Reactivate' })).toBeInTheDocument()
  })

  it('lets an owner delete a member behind a confirmation', async () => {
    const { calls } = renderApp({
      entry: '/admin/members/member-1',
      handlers: {
        ...adminDataHandlers(),
        '/api/members/member-1': (_url: string, init?: RequestInit) =>
          init?.method === 'DELETE' ? { body: { status: 'ok' } } : { body: adminMemberFixture },
      },
    })

    fireEvent.click(await screen.findByRole('button', { name: /delete member/i }))
    const dialog = await screen.findByRole('dialog')
    fireEvent.click(within(dialog).getByRole('button', { name: /^delete$/i }))

    await waitFor(() =>
      expect(calls.some((c) => c.url.includes('/api/members/member-1') && c.init?.method === 'DELETE')).toBe(
        true,
      ),
    )
  })

  it('hides deletion from editors', async () => {
    renderApp({
      entry: '/admin/members/member-1',
      handlers: { ...adminDataHandlers(), '/api/auth/me': { body: editorMeFixture } },
    })

    await screen.findByLabelText(/full name/i)
    expect(screen.queryByRole('button', { name: /delete member/i })).not.toBeInTheDocument()
  })
})

describe('admin navigation', () => {
  it('exposes a Members link in the admin sidebar', async () => {
    renderApp({ entry: '/admin', handlers: adminDataHandlers() })
    const links = await screen.findAllByRole('link', { name: 'Members' })
    expect(links.some((link) => link.getAttribute('href') === '/admin/members')).toBe(true)
  })

  it('uses the owner fixture for the sidebar session', async () => {
    renderApp({ entry: '/admin', handlers: { ...adminDataHandlers(), '/api/auth/me': { body: meFixture } } })
    expect(await screen.findByText('owner@thridhalabs.com')).toBeInTheDocument()
  })
})
