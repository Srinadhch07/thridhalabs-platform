/**
 * Member contributions to official Projects — member publication-review
 * submit/withdraw/resubmit, the admin review queue + decision flow (RBAC,
 * mandatory feedback, featuring) and the merge of featured contributions into
 * the public Projects page.
 */

import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { editorMeFixture, memberMeFixture, memberWorkFixture, meFixture } from './fixtures'
import { renderApp } from './helpers'
import type { HandlerMap } from './helpers'
import type { AdminWorkCard, AdminWorkDetail, FeaturedContribution } from '../types/work'

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

const adminCard = (overrides: Partial<AdminWorkCard> = {}): AdminWorkCard => ({
  id: 'w-1',
  member_id: memberMeFixture.member_id,
  member_name: 'Ada Lovelace',
  title: 'Embodied Agents',
  slug: 'embodied-agents',
  summary: 'A study of embodied AI agents.',
  cover_media_id: null,
  tags: ['Robotics', 'AI'],
  visibility: 'public',
  publication_status: 'pending_review',
  version: 2,
  submitted_at: '2026-02-02T10:00:00Z',
  review_feedback: null,
  reviewed_at: null,
  featured_on_projects: false,
  featured_classification: null,
  featured_at: null,
  published_at: null,
  created_at: '2026-01-10T00:00:00Z',
  updated_at: '2026-02-02T10:00:00Z',
  ...overrides,
})

const adminDetail = (overrides: Partial<AdminWorkDetail> = {}): AdminWorkDetail => ({
  ...adminCard(),
  external_links: [],
  content: { version: 1, blocks: [] },
  ...overrides,
})

const contribution = (overrides: Partial<FeaturedContribution> = {}): FeaturedContribution => ({
  slug: 'embodied-agents',
  title: 'Embodied Agents',
  summary: 'A study of embodied AI agents.',
  cover_media_id: null,
  tags: ['Robotics', 'AI'],
  classification: 'member-contribution',
  featured_at: '2026-02-03T00:00:00Z',
  published_at: '2026-02-02T00:00:00Z',
  author: {
    member_id: memberMeFixture.member_id,
    display_name: 'Ada Lovelace',
    picture_media_id: null,
  },
  ...overrides,
})

describe('member publication review', () => {
  it('submits a draft work for publication review', async () => {
    const draft = { ...memberWorkFixture, publication_status: 'draft' as const }
    const { calls } = renderApp({
      entry: '/member/works/w-1/edit',
      handlers: memberSession({
        '/api/member/works/w-1': { body: draft },
        '/api/member/works/w-1/submit': {
          body: { ...draft, publication_status: 'pending_review' },
        },
      }),
    })

    fireEvent.click(await screen.findByRole('button', { name: /submit for publication review/i }))

    await waitFor(() =>
      expect(
        calls.some(
          (c) => c.url.includes('/api/member/works/w-1/submit') && c.init?.method === 'POST',
        ),
      ).toBe(true),
    )
  })

  it('withdraws a pending submission', async () => {
    const pending = { ...memberWorkFixture, publication_status: 'pending_review' as const }
    const { calls } = renderApp({
      entry: '/member/works/w-1/edit',
      handlers: memberSession({
        '/api/member/works/w-1': { body: pending },
        '/api/member/works/w-1/withdraw': { body: { ...pending, publication_status: 'draft' } },
      }),
    })

    fireEvent.click(await screen.findByRole('button', { name: /withdraw submission/i }))

    await waitFor(() =>
      expect(
        calls.some(
          (c) => c.url.includes('/api/member/works/w-1/withdraw') && c.init?.method === 'POST',
        ),
      ).toBe(true),
    )
  })

  it('shows reviewer feedback and a resubmit action when changes are requested', async () => {
    const changes = {
      ...memberWorkFixture,
      publication_status: 'changes_requested' as const,
      review_feedback: 'Please expand the methods section.',
    }
    renderApp({
      entry: '/member/works/w-1/edit',
      handlers: memberSession({ '/api/member/works/w-1': { body: changes } }),
    })

    expect(await screen.findByText(/please expand the methods section/i)).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /resubmit for publication review/i }),
    ).toBeInTheDocument()
  })
})

describe('admin publication review queue', () => {
  it('lists pending works and links into the review detail', async () => {
    renderApp({
      entry: '/admin/works',
      handlers: adminSession({
        '/api/admin/works': { body: { items: [adminCard()], total: 1, page: 1, page_size: 20, pages: 1 } },
      }),
    })

    const link = await screen.findByRole('link', { name: 'Embodied Agents' })
    expect(link).toHaveAttribute('href', '/admin/works/w-1')
    expect(screen.getByText('Ada Lovelace')).toBeInTheDocument()
  })

  it('records an approval decision via POST', async () => {
    const { calls } = renderApp({
      entry: '/admin/works/w-1',
      handlers: adminSession({
        '/api/admin/works/w-1': { body: adminDetail() },
        '/api/admin/works/w-1/decision': {
          body: adminDetail({ publication_status: 'published', published_at: '2026-02-03T00:00:00Z' }),
        },
      }),
    })

    const group = await screen.findByRole('radiogroup', { name: /decision action/i })
    fireEvent.click(within(group).getByLabelText(/approve/i))
    fireEvent.click(screen.getByRole('button', { name: /submit decision/i }))

    await waitFor(() => {
      const post = calls.find(
        (c) => c.url.includes('/api/admin/works/w-1/decision') && c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(String(post!.init?.body))).toMatchObject({ action: 'approve' })
    })
  })

  it('requires feedback when requesting changes', async () => {
    const { calls } = renderApp({
      entry: '/admin/works/w-1',
      handlers: adminSession({ '/api/admin/works/w-1': { body: adminDetail() } }),
    })

    const group = await screen.findByRole('radiogroup', { name: /decision action/i })
    fireEvent.click(within(group).getByLabelText(/request changes/i))
    fireEvent.click(screen.getByRole('button', { name: /submit decision/i }))

    expect(await screen.findByText(/feedback is required/i)).toBeInTheDocument()
    expect(
      calls.some((c) => c.url.includes('/decision') && c.init?.method === 'POST'),
    ).toBe(false)
  })

  it('blocks editors from recording decisions', async () => {
    renderApp({
      entry: '/admin/works/w-1',
      handlers: adminSession({
        '/api/auth/me': { body: editorMeFixture },
        '/api/admin/works/w-1': { body: adminDetail() },
      }),
    })

    expect(
      await screen.findByText(/only admins and owners can record publication decisions/i),
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /submit decision/i })).not.toBeInTheDocument()
  })

  it('features a published, public work onto the Projects page', async () => {
    const { calls } = renderApp({
      entry: '/admin/works/w-1',
      handlers: adminSession({
        '/api/admin/works/w-1': {
          body: adminDetail({ publication_status: 'published', published_at: '2026-02-03T00:00:00Z' }),
        },
        '/api/admin/works/w-1/feature': {
          body: adminDetail({
            publication_status: 'published',
            published_at: '2026-02-03T00:00:00Z',
            featured_on_projects: true,
            featured_classification: 'member-contribution',
          }),
        },
      }),
    })

    fireEvent.click(await screen.findByRole('button', { name: /save featuring/i }))

    await waitFor(() => {
      const post = calls.find(
        (c) => c.url.includes('/api/admin/works/w-1/feature') && c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(String(post!.init?.body))).toMatchObject({
        featured: true,
        classification: 'member-contribution',
      })
    })
  })
})

describe('public Projects page — featured contributions', () => {
  it('renders a featured contribution with author attribution and a member-work link', async () => {
    renderApp({
      entry: '/projects',
      handlers: {
        '/api/public/projects': { body: { items: [], total: 0, page: 1, page_size: 24, pages: 0 } },
        '/api/public/contributions': { body: { items: [contribution()] } },
      },
    })

    const link = await screen.findByRole('link', {
      name: /view member contribution: embodied agents/i,
    })
    expect(link).toHaveAttribute('href', `/members/${memberMeFixture.member_id}/works/embodied-agents`)
    expect(within(link).getByText(/by ada lovelace/i)).toBeInTheDocument()
  })

  it('filters the index to member contributions only', async () => {
    renderApp({
      entry: '/projects?type=member-contribution',
      handlers: {
        '/api/public/projects': { body: { items: [], total: 0, page: 1, page_size: 24, pages: 0 } },
        '/api/public/contributions': { body: { items: [contribution()] } },
      },
    })

    expect(await screen.findByText('Embodied Agents')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Member contributions/ }),
    ).toHaveAttribute('aria-pressed', 'true')
  })
})
