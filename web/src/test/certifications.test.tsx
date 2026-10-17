/**
 * Certifications — member submissions/tracking and the admin review queue +
 * decision flow (RBAC, snapshot review, mandatory feedback).
 */

import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import {
  adminDataHandlers,
  certificationDetailFixture,
  certificationListFixture,
  editorMeFixture,
  memberMeFixture,
  meFixture,
  workListFixture,
} from './fixtures'
import { renderApp } from './helpers'
import type { HandlerMap } from './helpers'

const csrf = {
  '/api/auth/csrf': { body: { csrfToken: 'test-csrf' } },
  '/api/member/csrf': { body: { csrfToken: 'test-csrf' } },
}

const memberSession = (overrides: HandlerMap = {}): HandlerMap => ({
  ...csrf,
  '/api/member/me': { body: memberMeFixture },
  ...overrides,
})

const adminSession = (overrides: HandlerMap = {}): HandlerMap => ({
  ...csrf,
  '/api/auth/me': { body: meFixture },
  ...overrides,
})

describe('member certifications', () => {
  it('lists the member certification requests with status', async () => {
    renderApp({
      entry: '/member/certifications',
      handlers: memberSession({
        '/api/member/certifications': { body: certificationListFixture() },
      }),
    })

    expect(await screen.findByText('Embodied Agents')).toBeInTheDocument()
    expect(screen.getAllByText('Submitted').length).toBeGreaterThan(0)
  })

  it('sends the status filter to the backend', async () => {
    const { calls } = renderApp({
      entry: '/member/certifications',
      handlers: memberSession({
        '/api/member/certifications': { body: certificationListFixture() },
      }),
    })

    const select = await screen.findByLabelText(/filter by status/i)
    fireEvent.change(select, { target: { value: 'approved' } })

    await waitFor(() =>
      expect(
        calls.some(
          (c) => c.url.includes('/api/member/certifications') && c.url.includes('status=approved'),
        ),
      ).toBe(true),
    )
  })

  it('expands a request to load its frozen snapshot', async () => {
    renderApp({
      entry: '/member/certifications',
      handlers: memberSession({
        '/api/member/certifications': { body: certificationListFixture() },
        '/api/member/certifications/cert-1': { body: certificationDetailFixture },
      }),
    })

    fireEvent.click(await screen.findByRole('button', { name: /view details/i }))

    expect(await screen.findByText(/submitted snapshot/i)).toBeInTheDocument()
    expect(screen.getByText(/no reviewer actions recorded yet/i)).toBeInTheDocument()
  })

  it('shows a Start Certification Request action', async () => {
    renderApp({
      entry: '/member/certifications',
      handlers: memberSession({
        '/api/member/certifications': { body: certificationListFixture() },
      }),
    })

    const start = await screen.findByRole('link', { name: /start certification request/i })
    expect(start).toHaveAttribute('href', '/member/works')
  })

  it('navigates to the Work Showcase when starting a request', async () => {
    renderApp({
      entry: '/member/certifications',
      handlers: memberSession({
        '/api/member/certifications': { body: certificationListFixture() },
        '/api/member/works': { body: workListFixture([]) },
      }),
    })

    fireEvent.click(await screen.findByRole('link', { name: /start certification request/i }))

    expect(await screen.findByRole('heading', { name: 'Work Showcase' })).toBeInTheDocument()
  })

  it('provides the Start Certification Request action in the empty state', async () => {
    renderApp({
      entry: '/member/certifications',
      handlers: memberSession({
        '/api/member/certifications': { body: certificationListFixture([]) },
      }),
    })

    expect(await screen.findByText(/no certification requests yet/i)).toBeInTheDocument()
    const starts = screen.getAllByRole('link', { name: /start certification request/i })
    expect(starts.length).toBeGreaterThan(0)
    starts.forEach((link) => expect(link).toHaveAttribute('href', '/member/works'))
  })

  it('shows an explicit error when the certification list fails to load', async () => {
    renderApp({
      entry: '/member/certifications',
      handlers: memberSession({
        '/api/member/certifications': {
          status: 500,
          body: { error: { code: 'SERVER_ERROR', message: 'Boom' } },
        },
      }),
    })

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
    expect(screen.queryByText(/no certification requests yet/i)).not.toBeInTheDocument()
  })
})

describe('admin certification review queue', () => {
  it('lists requests and links into the review detail', async () => {
    renderApp({
      entry: '/admin/certifications',
      handlers: adminSession({
        '/api/admin/certifications': { body: certificationListFixture() },
      }),
    })

    const link = await screen.findByRole('link', { name: 'Embodied Agents' })
    expect(link).toHaveAttribute('href', '/admin/certifications/cert-1')
    expect(screen.getByText('THL-M-2026-0001')).toBeInTheDocument()
  })

  it('records an approval decision via POST', async () => {
    const { calls } = renderApp({
      entry: '/admin/certifications/cert-1',
      handlers: adminSession({
        '/api/admin/certifications/cert-1': { body: certificationDetailFixture },
        '/api/admin/certifications/cert-1/decision': {
          body: { ...certificationDetailFixture, status: 'approved', active: false },
        },
      }),
    })

    const group = await screen.findByRole('radiogroup', { name: /decision action/i })
    fireEvent.click(within(group).getByLabelText(/approve/i))
    fireEvent.click(screen.getByRole('button', { name: /submit decision/i }))

    await waitFor(() => {
      const post = calls.find(
        (c) =>
          c.url.includes('/api/admin/certifications/cert-1/decision') && c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(String(post!.init?.body))).toMatchObject({ action: 'approve' })
    })
  })

  it('requires feedback when rejecting', async () => {
    const { calls } = renderApp({
      entry: '/admin/certifications/cert-1',
      handlers: adminSession({
        '/api/admin/certifications/cert-1': { body: certificationDetailFixture },
      }),
    })

    const group = await screen.findByRole('radiogroup', { name: /decision action/i })
    fireEvent.click(within(group).getByLabelText(/reject/i))
    fireEvent.click(screen.getByRole('button', { name: /submit decision/i }))

    expect(await screen.findByText(/feedback is required/i)).toBeInTheDocument()
    expect(
      calls.some((c) => c.url.includes('/decision') && c.init?.method === 'POST'),
    ).toBe(false)
  })

  it('blocks editors from recording decisions', async () => {
    renderApp({
      entry: '/admin/certifications/cert-1',
      handlers: adminSession({
        '/api/auth/me': { body: editorMeFixture },
        '/api/admin/certifications/cert-1': { body: certificationDetailFixture },
      }),
    })

    expect(await screen.findByText(/only admins and owners can record/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /submit decision/i })).not.toBeInTheDocument()
  })

  it('shows that a decided request needs no further action', async () => {
    renderApp({
      entry: '/admin/certifications/cert-1',
      handlers: adminSession({
        '/api/admin/certifications/cert-1': {
          body: { ...certificationDetailFixture, status: 'approved', active: false },
        },
      }),
    })

    expect(await screen.findByText(/this request has been decided/i)).toBeInTheDocument()
  })

  it('notes a changes_requested request is awaiting resubmission', async () => {
    renderApp({
      entry: '/admin/certifications/cert-1',
      handlers: adminSession({
        '/api/admin/certifications/cert-1': {
          body: { ...certificationDetailFixture, status: 'changes_requested', active: true },
        },
      }),
    })

    expect(await screen.findByText(/awaiting the member’s resubmission/i)).toBeInTheDocument()
  })
})

describe('admin navigation', () => {
  it('exposes a Certifications link in the admin sidebar', async () => {
    renderApp({ entry: '/admin', handlers: adminDataHandlers() })
    const links = await screen.findAllByRole('link', { name: 'Certifications' })
    expect(links.some((link) => link.getAttribute('href') === '/admin/certifications')).toBe(true)
  })
})

describe('member navigation', () => {
  it('exposes Work Showcase and Certifications in the member sidebar', async () => {
    renderApp({
      entry: '/member/works',
      handlers: memberSession({ '/api/member/works': { body: { items: [], total: 0, page: 1, page_size: 12, pages: 0 } } }),
    })
    const works = await screen.findByRole('link', { name: /work showcase/i })
    expect(works).toHaveAttribute('href', '/member/works')
    const certs = screen.getByRole('link', { name: /^certifications$/i })
    expect(certs).toHaveAttribute('href', '/member/certifications')
  })
})
