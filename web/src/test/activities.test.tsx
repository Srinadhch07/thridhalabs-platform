/**
 * Activity management — public index/detail, the homepage featured carousel,
 * the admin roster/invitations/brief flows and member self-registration.
 */

import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import {
  activityParticipantsFixture,
  adminActivitiesFixture,
  adminActivityFixture,
  bannerMediaFixture,
  inviteMembersPool,
  memberActivityFixture,
  memberMeFixture,
  meFixture,
  publicActivitiesFixture,
  publicActivityFixture,
} from './fixtures'
import { renderApp } from './helpers'
import type { HandlerMap, MockHandler } from './helpers'
import type { AdminActivity, PublicActivity } from '../types/activity'

const csrf = {
  '/api/auth/csrf': { body: { csrfToken: 'test-csrf' } },
  '/api/member/csrf': { body: { csrfToken: 'test-csrf' } },
}

const adminSession = (overrides: HandlerMap = {}): HandlerMap => ({
  ...csrf,
  '/api/auth/me': { body: meFixture },
  ...overrides,
})

const memberSession = (overrides: HandlerMap = {}): HandlerMap => ({
  ...csrf,
  '/api/member/me': { body: memberMeFixture },
  ...overrides,
})

const adminActivityHandlers = (
  overrides: Partial<AdminActivity> = {},
  extra: HandlerMap = {},
): HandlerMap =>
  adminSession({
    '/api/admin/activities/a-1': { body: { ...adminActivityFixture, ...overrides } },
    '/api/admin/activities/a-1/participants': { body: activityParticipantsFixture() },
    ...extra,
  })

/** Server-style members endpoint: filters by search, paginates. */
const membersSearchHandler = (url: string): MockHandler => {
  const params = new URL(url, 'http://localhost').searchParams
  const search = (params.get('search') ?? '').toLowerCase()
  const page = Number(params.get('page') ?? '1')
  const pageSize = Number(params.get('page_size') ?? '10')
  const all = inviteMembersPool()
  const filtered = search
    ? all.filter((m) =>
        [m.full_name, m.email, m.role_label, m.member_id].some((value) =>
          (value ?? '').toLowerCase().includes(search),
        ),
      )
    : all
  const start = (page - 1) * pageSize
  return {
    body: {
      items: filtered.slice(start, start + pageSize),
      total: filtered.length,
      page,
      page_size: pageSize,
      pages: Math.ceil(filtered.length / pageSize),
    },
  }
}

/** Published project with the searchable members pool wired in. */
const projectActivityHandlers = (
  extra: HandlerMap = {},
  overrides: Partial<AdminActivity> = {},
): HandlerMap =>
  adminActivityHandlers(
    { activity_type: 'project', status: 'published', ...overrides },
    {
      '/api/members': membersSearchHandler,
      ...extra,
    },
  )

describe('public activities index', () => {
  it('lists a published activity with its type and presentation label', async () => {
    renderApp({
      entry: '/activities',
      handlers: { '/api/public/activities': { body: publicActivitiesFixture() } },
    })

    const link = await screen.findByRole('link', { name: /view activity: ai builders/i })
    expect(link).toHaveAttribute('href', '/activities/ai-builders-programme-2026')
    expect(screen.getByText('PROGRAMME')).toBeInTheDocument()
    expect(screen.getByText('Coming soon')).toBeInTheDocument()
  })

  it('renders the banner image on a public activity card', async () => {
    const withBanner: PublicActivity = { ...publicActivityFixture, banner_media_id: 'banner-1' }
    renderApp({
      entry: '/activities',
      handlers: {
        '/api/public/activities': {
          body: { items: [withBanner], total: 1, page: 1, page_size: 12, pages: 1 },
        },
      },
    })

    const img = await screen.findByAltText(/ai builders programme 2026 visual/i)
    expect(img).toBeInTheDocument()
    expect(img).toHaveAttribute('src', expect.stringContaining('/api/public/media/banner-1'))
    // Promotional banners keep their natural ratio (no cover crop).
    expect(img.closest('.media-tile')).toHaveClass('media-tile--natural')
    expect(img.closest('.activity-card__media')).toBeTruthy()
  })

  it('renders the full uncropped banner on the activity detail page', async () => {
    const withBanner: PublicActivity = { ...publicActivityFixture, banner_media_id: 'banner-1' }
    renderApp({
      entry: '/activities/ai-builders-programme-2026',
      handlers: { '/api/public/activities/ai-builders-programme-2026': { body: withBanner } },
    })

    const img = await screen.findByAltText(/ai builders programme 2026 visual/i)
    expect(img.closest('.media-tile')).toHaveClass('media-tile--natural')
    expect(img.closest('.activity-banner')).toBeTruthy()
  })

  it('marks a cancelled activity on its detail page', async () => {
    const cancelled: PublicActivity = {
      ...publicActivityFixture,
      slug: 'summer-hack',
      title: 'Summer Hack',
      activity_type: 'hackathon',
      presentation_status: 'cancelled',
      registration_open: false,
    }
    renderApp({
      entry: '/activities/summer-hack',
      handlers: { '/api/public/activities/summer-hack': { body: cancelled } },
    })

    expect(await screen.findByText(/this activity has been cancelled/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Summer Hack' })).toBeInTheDocument()
  })
})

describe('homepage featured carousel', () => {
  it('shows a featured published activity and links to its detail page', async () => {
    renderApp({
      entry: '/',
      handlers: { '/api/public/activities': { body: publicActivitiesFixture() } },
    })

    const link = await screen.findByRole('link', { name: /view activity: ai builders/i })
    expect(link).toHaveAttribute('href', '/activities/ai-builders-programme-2026')
  })

  it('requests only featured activities', async () => {
    const { calls } = renderApp({
      entry: '/',
      handlers: { '/api/public/activities': { body: publicActivitiesFixture() } },
    })

    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes('/api/public/activities') && c.url.includes('featured=true')),
      ).toBe(true),
    )
  })

  it('exposes accessible carousel controls linking to each activity', async () => {
    const two: PublicActivity = {
      ...publicActivityFixture,
      slug: 'summer-hack',
      title: 'Summer Hack',
    }
    renderApp({
      entry: '/',
      handlers: {
        '/api/public/activities': {
          body: { items: [publicActivityFixture, two], total: 2, page: 1, page_size: 12, pages: 1 },
        },
      },
    })

    expect(await screen.findByRole('button', { name: /next activities/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /previous activities/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /view activity: summer hack/i })).toHaveAttribute(
      'href',
      '/activities/summer-hack',
    )
  })

  it('hides the section when nothing is featured', async () => {
    const { calls } = renderApp({
      entry: '/',
      handlers: {
        '/api/public/activities': {
          body: { items: [], total: 0, page: 1, page_size: 12, pages: 0 },
        },
      },
    })

    await screen.findByRole('heading', { level: 1, name: /thridha labs/i })
    await waitFor(() =>
      expect(calls.some((c) => c.url.includes('/api/public/activities'))).toBe(true),
    )
    expect(screen.queryByRole('link', { name: /view activity/i })).not.toBeInTheDocument()
  })
})

describe('admin activities', () => {
  it('lists an activity and links into the editor', async () => {
    renderApp({
      entry: '/admin/activities',
      handlers: adminSession({ '/api/admin/activities': { body: adminActivitiesFixture() } }),
    })

    const link = await screen.findByRole('link', { name: adminActivityFixture.title })
    expect(link).toHaveAttribute('href', '/admin/activities/a-1')
    expect(screen.getByRole('link', { name: 'View' })).toHaveAttribute(
      'href',
      '/activities/ai-builders-programme-2026',
    )
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument()
  })

  it('publishes a draft activity through the editor form', async () => {
    const draft: Partial<AdminActivity> = {
      status: 'draft',
      published_at: null,
      brief: null,
      brief_history_count: 0,
    }
    const { calls } = renderApp({
      entry: '/admin/activities/a-1',
      handlers: adminActivityHandlers(draft),
    })

    await screen.findByRole('button', { name: /save changes/i })
    const statusSelect = screen.getByLabelText('Status')
    fireEvent.change(statusSelect, { target: { value: 'published' } })
    fireEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => {
      const patch = calls.find(
        (c) => c.url.includes('/api/admin/activities/a-1') && c.init?.method === 'PATCH',
      )
      expect(patch).toBeTruthy()
      expect(JSON.parse(String(patch!.init?.body))).toMatchObject({ status: 'published' })
    })
  })

  it('uploads a PDF brief to the brief endpoint', async () => {
    const { calls } = renderApp({
      entry: '/admin/activities/a-1',
      handlers: adminActivityHandlers(
        {},
        {
          '/api/admin/activities/a-1/brief': {
            body: {
              ...adminActivityFixture,
              brief: { version: 2, filename: 'brief.pdf', size_bytes: 8, uploaded_at: '2026-02-04T00:00:00Z' },
              brief_history_count: 2,
            },
          },
        },
      ),
    })

    await screen.findByRole('button', { name: /replace brief/i })
    const input = document.getElementById('activity-brief-input') as HTMLInputElement
    expect(input).toBeTruthy()
    const file = new File(['%PDF-1.4'], 'brief.pdf', { type: 'application/pdf' })
    Object.defineProperty(input, 'files', { value: [file], configurable: true })
    fireEvent.change(input)

    await waitFor(() =>
      expect(
        calls.some(
          (c) => c.url.includes('/api/admin/activities/a-1/brief') && c.init?.method === 'POST',
        ),
      ).toBe(true),
    )
  })

  it('renders a framed banner preview for an existing banner', async () => {
    renderApp({
      entry: '/admin/activities/a-1',
      handlers: adminActivityHandlers(
        { banner_media_id: 'banner-1' },
        { '/api/media/banner-1': { body: bannerMediaFixture } },
      ),
    })

    const img = await screen.findByAltText('Promotional banner')
    expect(img).toBeInTheDocument()
    expect(img.closest('.image-upload--framed')).toBeTruthy()
  })

  it('updates a participant status through the roster', async () => {
    const { calls } = renderApp({
      entry: '/admin/activities/a-1',
      handlers: adminActivityHandlers(),
    })

    const saveButtons = await screen.findAllByRole('button', { name: 'Save' })
    const statusSelect = screen.getByLabelText(/status for thl-m-2026-0001/i)
    fireEvent.change(statusSelect, { target: { value: 'withdrawn' } })
    fireEvent.click(saveButtons[0])

    await waitFor(() => {
      const patch = calls.find(
        (c) =>
          c.url.includes('/api/admin/activities/a-1/participants/part-1') &&
          c.init?.method === 'PATCH',
      )
      expect(patch).toBeTruthy()
      expect(JSON.parse(String(patch!.init?.body))).toMatchObject({ status: 'withdrawn' })
    })
  })
})

describe('admin project invitations — member selection', () => {
  it('searches members by name across the whole dataset', async () => {
    const { calls } = renderApp({
      entry: '/admin/activities/a-1',
      handlers: projectActivityHandlers(),
    })

    const input = await screen.findByLabelText('Search members')
    fireEvent.change(input, { target: { value: 'grace' } })

    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes('/api/members') && c.url.includes('search=grace')),
      ).toBe(true),
    )
    expect(await screen.findByText('Grace Hopper')).toBeInTheDocument()
    expect(screen.queryByText('Alan Turing')).not.toBeInTheDocument()
  })

  it('searches members by email', async () => {
    const { calls } = renderApp({
      entry: '/admin/activities/a-1',
      handlers: projectActivityHandlers(),
    })

    const input = await screen.findByLabelText('Search members')
    fireEvent.change(input, { target: { value: 'katherine@' } })

    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes('/api/members') && c.url.includes('search=katherine')),
      ).toBe(true),
    )
    expect(await screen.findByText('Katherine Johnson')).toBeInTheDocument()
    expect(screen.queryByText('Grace Hopper')).not.toBeInTheDocument()
  })

  it('searches members by role', async () => {
    const { calls } = renderApp({
      entry: '/admin/activities/a-1',
      handlers: projectActivityHandlers(),
    })

    const input = await screen.findByLabelText('Search members')
    fireEvent.change(input, { target: { value: 'developer' } })

    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes('/api/members') && c.url.includes('search=developer')),
      ).toBe(true),
    )
    // Frontend + Backend developers match; the product analyst does not.
    expect(await screen.findByText('Grace Hopper')).toBeInTheDocument()
    expect(screen.getByText('Alan Turing')).toBeInTheDocument()
    expect(screen.queryByText('Katherine Johnson')).not.toBeInTheDocument()
  })

  it('shows the total and paginates through the full dataset', async () => {
    const { calls } = renderApp({
      entry: '/admin/activities/a-1',
      handlers: projectActivityHandlers(),
    })

    expect(await screen.findByText('12 members')).toBeInTheDocument()
    expect(screen.getByText(/page 1 of 2/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes('/api/members') && c.url.includes('page=2')),
      ).toBe(true),
    )
  })

  it('preserves selections across pages and search changes', async () => {
    const { calls } = renderApp({
      entry: '/admin/activities/a-1',
      handlers: projectActivityHandlers(),
    })

    fireEvent.click(await screen.findByLabelText(/select grace hopper/i))
    expect(await screen.findByText('1 selected')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    const input = screen.getByLabelText('Search members')
    fireEvent.change(input, { target: { value: 'alan' } })
    await waitFor(() =>
      expect(calls.some((c) => c.url.includes('/api/members') && c.url.includes('search=alan'))).toBe(
        true,
      ),
    )

    // Grace is no longer in the results, but stays selected.
    expect(screen.getByText('1 selected')).toBeInTheDocument()
    expect(screen.getByText('Grace Hopper')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /send 1 invitation/i })).toBeInTheDocument()
  })

  it('allows removing a selected member before sending', async () => {
    renderApp({
      entry: '/admin/activities/a-1',
      handlers: projectActivityHandlers(),
    })

    fireEvent.click(await screen.findByLabelText(/select grace hopper/i))
    await screen.findByRole('button', { name: /send 1 invitation/i })

    fireEvent.click(screen.getByRole('button', { name: /remove grace hopper/i }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /^send invitations$/i })).toBeInTheDocument(),
    )
  })

  it('blocks members who are already participants', async () => {
    renderApp({
      entry: '/admin/activities/a-1',
      handlers: projectActivityHandlers(),
    })

    // member-1 (Ada) is already a confirmed participant in the fixture.
    const ada = await screen.findByLabelText(/select ada lovelace/i)
    expect(ada).toBeDisabled()
    expect(screen.getAllByText('Confirmed').length).toBeGreaterThan(0)
  })

  it('does not allow selecting inactive or pending-setup members', async () => {
    renderApp({
      entry: '/admin/activities/a-1',
      handlers: projectActivityHandlers(),
    })

    expect(await screen.findByLabelText(/select ivan inactive/i)).toBeDisabled()
    expect(screen.getByLabelText(/select penny pending/i)).toBeDisabled()
  })

  it('assigns a project role to a selected member and sends the invitation', async () => {
    const { calls } = renderApp({
      entry: '/admin/activities/a-1',
      handlers: projectActivityHandlers({
        '/api/admin/activities/a-1/invitations': {
          body: { invited: 1, re_invited: 0, emails_sent: 1, email_failures: 0, skipped: [], errors: [] },
        },
      }),
    })

    fireEvent.click(await screen.findByLabelText(/select grace hopper/i))
    const roleSelect = await screen.findByLabelText(/role for grace hopper/i)
    fireEvent.change(roleSelect, { target: { value: 'AI Engineer' } })

    fireEvent.click(screen.getByRole('button', { name: /send 1 invitation/i }))

    await waitFor(() => {
      const post = calls.find(
        (c) => c.url.includes('/api/admin/activities/a-1/invitations') && c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(String(post!.init?.body))).toMatchObject({
        invitations: [{ member_id: 'member-2', role: 'AI Engineer' }],
      })
    })
  })
})

describe('member activities portal', () => {
  it('self-registers for an open programme', async () => {
    const { calls } = renderApp({
      entry: '/member/activities',
      handlers: memberSession({
        '/api/member/activities': { body: { items: [memberActivityFixture] } },
        '/api/member/activities/ai-builders-programme-2026/register': {
          body: { ...memberActivityFixture, can_register: false, participation_status: 'confirmed' },
        },
      }),
    })

    fireEvent.click(await screen.findByRole('button', { name: /^join$/i }))

    await waitFor(() => {
      const post = calls.find(
        (c) =>
          c.url.includes('/api/member/activities/ai-builders-programme-2026/register') &&
          c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
    })
  })

  it('offers a withdraw action once registered', async () => {
    const registered = {
      ...memberActivityFixture,
      can_register: false,
      can_withdraw: true,
      participation_status: 'confirmed' as const,
      participation_role: 'AI Engineer',
    }
    const { calls } = renderApp({
      entry: '/member/activities',
      handlers: memberSession({
        '/api/member/activities': { body: { items: [registered] } },
        '/api/member/activities/ai-builders-programme-2026/withdraw': {
          body: { ...registered, can_register: true, can_withdraw: false, participation_status: null },
        },
      }),
    })

    expect(await screen.findByText(/role: ai engineer/i)).toBeInTheDocument()
    fireEvent.click(await screen.findByRole('button', { name: /withdraw/i }))

    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.url.includes('/api/member/activities/ai-builders-programme-2026/withdraw') &&
            c.init?.method === 'POST',
        ),
      ).toBe(true)
    })
  })
})
