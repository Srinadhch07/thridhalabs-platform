/**
 * Work Showcase — member works dashboard and the block-based work editor:
 * listing/filtering, create, edit, publish/unpublish and certification submit.
 */

import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import {
  memberMeFixture,
  memberWorkFixture,
  workCardFixture,
  workCertificationRefFixture,
  workListFixture,
} from './fixtures'
import { renderApp } from './helpers'
import type { HandlerMap } from './helpers'

const csrf = {
  '/api/auth/csrf': { body: { csrfToken: 'test-csrf' } },
  '/api/member/csrf': { body: { csrfToken: 'test-csrf' } },
}
const memberMedia = { '/api/member/media': { body: { items: [], total: 0, page: 1, page_size: 24, pages: 0 } } }

const memberSession = (overrides: HandlerMap = {}): HandlerMap => ({
  ...csrf,
  '/api/member/me': { body: memberMeFixture },
  ...memberMedia,
  ...overrides,
})

describe('member work showcase', () => {
  it('lists the member works with status and visibility chips', async () => {
    renderApp({
      entry: '/member/works',
      handlers: memberSession({ '/api/member/works': { body: workListFixture() } }),
    })

    const link = await screen.findByRole('link', { name: /open work: embodied agents/i })
    expect(link).toHaveAttribute('href', '/member/works/w-1/edit')
    expect(within(link).getByText('Published')).toBeInTheDocument()
    expect(within(link).getByText('Public')).toBeInTheDocument()
  })

  it('shows the empty state when there are no works', async () => {
    renderApp({
      entry: '/member/works',
      handlers: memberSession({ '/api/member/works': { body: workListFixture([]) } }),
    })

    expect(await screen.findByText(/no works yet/i)).toBeInTheDocument()
  })

  it('sends the publication status filter to the backend', async () => {
    const { calls } = renderApp({
      entry: '/member/works',
      handlers: memberSession({ '/api/member/works': { body: workListFixture() } }),
    })

    const select = await screen.findByLabelText(/filter by status/i)
    fireEvent.change(select, { target: { value: 'published' } })

    await waitFor(() =>
      expect(
        calls.some(
          (c) => c.url.includes('/api/member/works') && c.url.includes('status=published'),
        ),
      ).toBe(true),
    )
  })

  it('shows Apply for Certification on an eligible published work', async () => {
    const reviewable = {
      ...workCardFixture,
      certification: { ...workCertificationRefFixture, reviewable: true },
    }
    renderApp({
      entry: '/member/works',
      handlers: memberSession({ '/api/member/works': { body: workListFixture([reviewable]) } }),
    })

    const apply = await screen.findByRole('link', { name: /apply for certification/i })
    expect(apply).toHaveAttribute('href', '/member/works/w-1/edit#certification')
  })

  it('opens the work editor certification section when Apply is clicked', async () => {
    const reviewable = {
      ...workCardFixture,
      certification: { ...workCertificationRefFixture, reviewable: true },
    }
    renderApp({
      entry: '/member/works',
      handlers: memberSession({
        '/api/member/works': { body: workListFixture([reviewable]) },
        '/api/member/works/w-1': {
          body: { ...memberWorkFixture, certification: reviewable.certification },
        },
      }),
    })

    fireEvent.click(await screen.findByRole('link', { name: /apply for certification/i }))

    expect(
      await screen.findByRole('button', { name: /submit for certification review/i }),
    ).toBeInTheDocument()
  })

  it('explains that a draft work must be published before applying', async () => {
    const draft = {
      ...workCardFixture,
      publication_status: 'draft' as const,
      certification: { ...workCertificationRefFixture, reviewable: false },
    }
    renderApp({
      entry: '/member/works',
      handlers: memberSession({ '/api/member/works': { body: workListFixture([draft]) } }),
    })

    expect(
      await screen.findByText(/publish this work to apply for certification/i),
    ).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /apply for certification/i })).not.toBeInTheDocument()
  })

  it('shows the request status instead of an Apply action while a review is active', async () => {
    const active = {
      ...workCardFixture,
      certification: {
        ...workCertificationRefFixture,
        status: 'under_review' as const,
        request_id: 'cert-1',
        reviewable: false,
      },
    }
    renderApp({
      entry: '/member/works',
      handlers: memberSession({ '/api/member/works': { body: workListFixture([active]) } }),
    })

    expect(await screen.findByText('Request Under Review')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /apply for certification/i })).not.toBeInTheDocument()
  })

  it('offers Request a New Review when resubmission is permitted', async () => {
    const reviewed = {
      ...workCardFixture,
      certification: {
        ...workCertificationRefFixture,
        status: 'changes_requested' as const,
        request_id: 'cert-1',
        feedback: 'Please revise.',
        changed_since_review: true,
        reviewable: true,
      },
    }
    renderApp({
      entry: '/member/works',
      handlers: memberSession({ '/api/member/works': { body: workListFixture([reviewed]) } }),
    })

    const action = await screen.findByRole('link', { name: /request a new review/i })
    expect(action).toHaveAttribute('href', '/member/works/w-1/edit#certification')
    expect(screen.queryByRole('link', { name: /apply for certification/i })).not.toBeInTheDocument()
  })

  it('keeps the card action outside the card link', async () => {
    const reviewable = {
      ...workCardFixture,
      certification: { ...workCertificationRefFixture, reviewable: true },
    }
    renderApp({
      entry: '/member/works',
      handlers: memberSession({ '/api/member/works': { body: workListFixture([reviewable]) } }),
    })

    const cardLink = await screen.findByRole('link', { name: /open work: embodied agents/i })
    const apply = screen.getByRole('link', { name: /apply for certification/i })
    expect(cardLink.contains(apply)).toBe(false)
  })

  it('keeps the work-card and editor eligibility states consistent', async () => {
    const reviewable = {
      ...workCardFixture,
      certification: { ...workCertificationRefFixture, reviewable: true },
    }
    renderApp({
      entry: '/member/works',
      handlers: memberSession({
        '/api/member/works': { body: workListFixture([reviewable]) },
        '/api/member/works/w-1': {
          body: { ...memberWorkFixture, certification: reviewable.certification },
        },
      }),
    })

    // Card says eligible…
    fireEvent.click(await screen.findByRole('link', { name: /apply for certification/i }))

    // …and the editor agrees: submit available, not "already active".
    expect(
      await screen.findByRole('button', { name: /submit for certification review/i }),
    ).toBeInTheDocument()
    expect(screen.getByText(/not submitted for review/i)).toBeInTheDocument()
    expect(screen.queryByText(/already has an active certification request/i)).not.toBeInTheDocument()
  })
})

describe('member work editor', () => {
  it('creates a work via POST /api/member/works', async () => {
    const { calls } = renderApp({
      entry: '/member/works/new',
      handlers: memberSession({
        '/api/member/works': (_url: string, init?: RequestInit) =>
          init?.method === 'POST'
            ? { status: 201, body: memberWorkFixture }
            : { body: workListFixture() },
      }),
    })

    const title = await screen.findByLabelText(/^title/i)
    fireEvent.change(title, { target: { value: 'Embodied Agents' } })
    fireEvent.change(screen.getByLabelText(/^summary/i), { target: { value: 'A study.' } })
    fireEvent.click(screen.getByRole('button', { name: /create work/i }))

    await waitFor(() => {
      const post = calls.find(
        (c) => c.url.endsWith('/api/member/works') && c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(String(post!.init?.body))).toMatchObject({
        title: 'Embodied Agents',
        summary: 'A study.',
      })
    })
  })

  it('requires a title before saving', async () => {
    const { calls } = renderApp({
      entry: '/member/works/new',
      handlers: memberSession(),
    })

    await screen.findByLabelText(/^title/i)
    fireEvent.click(screen.getByRole('button', { name: /create work/i }))

    expect(await screen.findByText(/a title is required/i)).toBeInTheDocument()
    expect(calls.some((c) => c.init?.method === 'POST')).toBe(false)
  })

  it('loads and updates a work via PATCH /api/member/works/:id', async () => {
    const { calls } = renderApp({
      entry: '/member/works/w-1/edit',
      handlers: memberSession({
        '/api/member/works/w-1': (_url: string, init?: RequestInit) =>
          init?.method === 'PATCH' ? { body: memberWorkFixture } : { body: memberWorkFixture },
      }),
    })

    const title = await screen.findByLabelText(/^title/i)
    await waitFor(() => expect(title).toHaveValue('Embodied Agents'))
    fireEvent.change(title, { target: { value: 'Embodied Agents v2' } })
    fireEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => {
      const patch = calls.find(
        (c) => c.url.includes('/api/member/works/w-1') && c.init?.method === 'PATCH',
      )
      expect(patch).toBeTruthy()
      expect(JSON.parse(String(patch!.init?.body))).toMatchObject({ title: 'Embodied Agents v2' })
    })
  })

  it('publishes a draft work via POST /api/member/works/:id/publish', async () => {
    const draft = { ...memberWorkFixture, publication_status: 'draft' as const, certification: { ...memberWorkFixture.certification } }
    const { calls } = renderApp({
      entry: '/member/works/w-1/edit',
      handlers: memberSession({
        '/api/member/works/w-1': { body: draft },
        '/api/member/works/w-1/publish': { body: { ...draft, publication_status: 'published' } },
      }),
    })

    fireEvent.click(await screen.findByRole('button', { name: 'Publish' }))

    await waitFor(() =>
      expect(calls.some((c) => c.url.includes('/api/member/works/w-1/publish'))).toBe(true),
    )
  })

  it('submits a published work for certification via POST /api/member/certifications', async () => {
    const reviewable = {
      ...memberWorkFixture,
      certification: { ...memberWorkFixture.certification, reviewable: true },
    }
    const { calls } = renderApp({
      entry: '/member/works/w-1/edit',
      handlers: memberSession({
        '/api/member/works/w-1': { body: reviewable },
        '/api/member/certifications': {
          status: 201,
          body: {
            id: 'cert-1',
            status: 'submitted',
            active: true,
            work: { id: 'w-1', title: 'Embodied Agents', slug: 'embodied-agents' },
            member: { member_id: 'THL-M-2026-0001', name: 'Ada Lovelace' },
            snapshot: { slug: 'embodied-agents', title: 'Embodied Agents', summary: 'A study.', cover_media_id: null, tags: [], external_links: [], content: { version: 1, blocks: [] } },
            snapshot_version: 2,
            version_reviewed: 0,
            changed_since_review: false,
            captured_at: '2026-02-02T09:59:00Z',
            submitted_at: '2026-02-02T10:00:00Z',
            decided_at: null,
            decided_by: null,
            decided_by_role: null,
            latest_feedback: null,
            decisions: [],
            created_at: '2026-02-02T09:59:00Z',
            updated_at: '2026-02-02T10:00:00Z',
          },
        },
      }),
    })

    fireEvent.click(await screen.findByRole('button', { name: /submit for certification/i }))

    await waitFor(() => {
      const post = calls.find(
        (c) => c.url.endsWith('/api/member/certifications') && c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(String(post!.init?.body))).toMatchObject({ work_id: 'w-1' })
    })
  })
})
