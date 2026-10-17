/** Careers — public page, nav/footer links, mailto apply links, admin CRUD. */

import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import {
  adminCareersSettingsFixture,
  adminDataHandlers,
  adminOpportunityFixture,
  editorMeFixture,
  enabledCareersSettingsFixture,
  opportunitiesFixture,
  publicOpportunityFixture,
} from './fixtures'
import { renderApp } from './helpers'

const enabledHandlers = (overrides: Record<string, unknown> = {}) => ({
  '/api/public/careers/settings': { body: enabledCareersSettingsFixture },
  '/api/public/careers/opportunities': { body: opportunitiesFixture() },
  ...overrides,
})

function expectedMailto(opportunity: typeof publicOpportunityFixture, template: string | null): string {
  const params = new URLSearchParams()
  params.set('subject', `Application — ${opportunity.title}`)
  if (template) params.set('body', template)
  return `mailto:${opportunity.application_email}?${params.toString()}`
}

describe('public careers page', () => {
  it('renders the enabled page with open roles and mailto apply links', async () => {
    renderApp({ entry: '/careers', handlers: enabledHandlers() })
    expect(
      await screen.findByRole('heading', { level: 1, name: /open roles at the lab/i }),
    ).toBeInTheDocument()
    expect(screen.getByText('Ways to work with the lab.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Lab Member' })).toBeInTheDocument()
    expect(screen.getByText('Build things alongside the lab.')).toBeInTheDocument()
    const apply = screen.getByRole('link', { name: 'Apply by email' })
    expect(apply).toHaveAttribute(
      'href',
      expectedMailto(publicOpportunityFixture, enabledCareersSettingsFixture.application_template),
    )
  })

  it('shows an empty state when enabled but no roles are open', async () => {
    renderApp({
      entry: '/careers',
      handlers: enabledHandlers({
        '/api/public/careers/opportunities': { body: { items: [], total: 0, page: 1, page_size: 20, pages: 0 } },
      }),
    })
    expect(await screen.findByText('No open roles right now')).toBeInTheDocument()
  })

  it('falls back to the 404 treatment when careers are disabled', async () => {
    const { calls } = renderApp({ entry: '/careers' })
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument())
    expect(calls.some((call) => call.url.includes('/api/public/careers/opportunities'))).toBe(false)
  })

  it('shows a retryable error state when the roles request fails', async () => {
    renderApp({
      entry: '/careers',
      handlers: enabledHandlers({
        '/api/public/careers/opportunities': { status: 500, body: { error: { code: 'INTERNAL', message: 'boom' } } },
      }),
    })
    expect(await screen.findByRole('heading', { name: 'Unable to load roles' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })

  it('hides the apply link when no application email resolves', async () => {
    renderApp({
      entry: '/careers',
      handlers: enabledHandlers({
        '/api/public/careers/opportunities': {
          body: {
            items: [{ ...publicOpportunityFixture, application_email: null }],
            total: 1, page: 1, page_size: 20, pages: 1,
          },
        },
      }),
    })
    expect(await screen.findByRole('heading', { name: 'Lab Member' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Apply by email' })).not.toBeInTheDocument()
    expect(screen.getByText('Applications are currently closed for this role.')).toBeInTheDocument()
  })

  it('sets the careers page title', async () => {
    renderApp({ entry: '/careers', handlers: enabledHandlers() })
    await waitFor(() => expect(document.title).toBe('Careers — Thridha Labs'))
  })
})

describe('careers navigation', () => {
  it('hides the Careers link while the feature is disabled', async () => {
    renderApp({ entry: '/' })
    await waitFor(() => expect(screen.getByRole('navigation', { name: 'Primary' })).toBeInTheDocument())
    expect(screen.queryByRole('link', { name: 'Careers' })).not.toBeInTheDocument()
  })

  it('shows the Careers link once enabled', async () => {
    renderApp({ entry: '/', handlers: enabledHandlers() })
    await waitFor(() =>
      expect(screen.getAllByRole('link', { name: 'Careers' }).length).toBeGreaterThan(0),
    )
  })
})

describe('admin careers settings', () => {
  it('loads, edits and saves the careers singleton via PUT', async () => {
    const { calls } = renderApp({ entry: '/admin/careers', handlers: adminDataHandlers() })
    const emailInput = await screen.findByLabelText(/application email/i)
    await waitFor(() => expect(emailInput).toHaveValue('apply@thridhalabs.com'))

    fireEvent.change(screen.getByLabelText(/^heading/i), { target: { value: 'Join the lab' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save careers settings' }))

    await waitFor(() => {
      const put = calls.find((call) => call.url.includes('/api/careers') && call.init?.method === 'PUT')
      expect(put).toBeTruthy()
    })
    const putCall = calls.find((call) => call.url.includes('/api/careers') && call.init?.method === 'PUT')
    expect(JSON.parse(String(putCall?.init?.body))).toMatchObject({
      enabled: true,
      heading: 'Join the lab',
      application_email: 'apply@thridhalabs.com',
    })
  })

  it('warns when enabled without a default application email', async () => {
    renderApp({
      entry: '/admin/careers',
      handlers: {
        ...adminDataHandlers(),
        '/api/careers': { body: { ...adminCareersSettingsFixture, enabled: true, application_email: null } },
      },
    })
    await waitFor(() =>
      expect(screen.getByText(/no default application email yet/i)).toBeInTheDocument(),
    )
  })

  it('shows the careers link in the admin navigation', async () => {
    renderApp({ entry: '/admin', handlers: adminDataHandlers() })
    await screen.findByRole('heading', { level: 1, name: /dashboard/i })
    expect(screen.getByRole('link', { name: 'Careers' })).toHaveAttribute('href', '/admin/careers')
  })
})

describe('admin opportunities', () => {
  it('lists opportunities with status and actions', async () => {
    renderApp({ entry: '/admin/careers/opportunities', handlers: adminDataHandlers() })
    expect(await screen.findByRole('heading', { level: 1, name: /opportunities/i })).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Lab Member' })).toBeInTheDocument()
    expect(await screen.findByText('Open', { selector: '.chip' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /add opportunity/i })).toHaveAttribute(
      'href',
      '/admin/careers/opportunities/new',
    )
  })

  it('prevents editors from deleting opportunities', async () => {
    renderApp({
      entry: '/admin/careers/opportunities',
      handlers: { ...adminDataHandlers(), '/api/auth/me': { body: editorMeFixture } },
    })
    expect(await screen.findByRole('heading', { level: 1, name: /opportunities/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument()
  })

  it('creates an opportunity with comma-separated skills and a custom type', async () => {
    const { calls } = renderApp({
      entry: '/admin/careers/opportunities/new',
      handlers: adminDataHandlers(),
    })
    const title = await screen.findByLabelText(/^title/i)
    fireEvent.change(title, { target: { value: 'Residency' } })
    fireEvent.change(screen.getByLabelText(/role type/i), { target: { value: 'other' } })
    fireEvent.change(screen.getByLabelText(/custom role type/i), { target: { value: 'Residency' } })
    fireEvent.change(screen.getByLabelText(/description/i), { target: { value: 'A slow arc of practice.' } })
    fireEvent.change(screen.getByLabelText(/skills/i), { target: { value: 'Python, LLMs' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create opportunity' }))

    await waitFor(() => {
      const post = calls.find(
        (call) => call.url.includes('/api/careers/opportunities') && call.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
    })
    const postCall = calls.find(
      (call) => call.url.includes('/api/careers/opportunities') && call.init?.method === 'POST',
    )
    expect(JSON.parse(String(postCall?.init?.body))).toMatchObject({
      title: 'Residency',
      type: 'other',
      custom_type: 'Residency',
      skills: ['Python', 'LLMs'],
      status: 'draft',
      display_order: 0,
    })
  })

  it('requires a custom role type before saving type “other”', async () => {
    renderApp({
      entry: '/admin/careers/opportunities/new',
      handlers: adminDataHandlers(),
    })
    const title = await screen.findByLabelText(/^title/i)
    fireEvent.change(title, { target: { value: 'Residency' } })
    fireEvent.change(screen.getByLabelText(/role type/i), { target: { value: 'other' } })
    const customType = screen.getByLabelText(/custom role type/i)
    fireEvent.change(customType, { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create opportunity' }))
    expect(await screen.findByText(/enter a custom role type/i)).toBeInTheDocument()
  })

  it('hydrates the editor from the API and saves edits via PATCH', async () => {
    const { calls } = renderApp({
      entry: '/admin/careers/opportunities/opp-1',
      handlers: adminDataHandlers(),
    })
    const title = await screen.findByLabelText(/^title/i)
    await waitFor(() => expect(title).toHaveValue('Lab Member'))

    fireEvent.change(screen.getByLabelText(/status/i), { target: { value: 'closed' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    await waitFor(() => {
      const patch = calls.find(
        (call) => call.url.includes('/api/careers/opportunities/opp-1') && call.init?.method === 'PATCH',
      )
      expect(patch).toBeTruthy()
    })
    const patchCall = calls.find(
      (call) => call.url.includes('/api/careers/opportunities/opp-1') && call.init?.method === 'PATCH',
    )
    expect(JSON.parse(String(patchCall?.init?.body))).toMatchObject({
      status: 'closed',
      title: 'Lab Member',
    })
  })

  it('warns when an open role has no resolvable application email', async () => {
    renderApp({
      entry: '/admin/careers/opportunities/opp-1',
      handlers: {
        ...adminDataHandlers(),
        '/api/careers': { body: { ...adminCareersSettingsFixture, application_email: null } },
        '/api/careers/opportunities/opp-1': { body: { ...adminOpportunityFixture, application_email: null } },
      },
    })
    expect(
      await screen.findByText(/no application email resolves/i),
    ).toBeInTheDocument()
  })
})