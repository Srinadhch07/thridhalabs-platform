/** Phase 7 admin panel tests — auth, dashboard, settings, branding, media,
 * clients, projects, testimonials, account, RBAC and session expiry. */

import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { adminBrandingFixture, adminDataHandlers, editorMeFixture, meFixture, pendingTestimonialFixture } from './fixtures'
import { renderApp } from './helpers'
import { BRANDING_CSS_VARS } from '../lib/utils/brandingTheme'

const NOT_AUTHENTICATED = { error: { code: 'NOT_AUTHENTICATED', message: 'Authentication required' } }

describe('admin login', () => {
  it('blocks unauthenticated access to /admin and shows the sign-in form', async () => {
    renderApp({ entry: '/admin' })
    expect(await screen.findByRole('heading', { level: 1, name: /sign in/i })).toBeInTheDocument()
  })

  it('signs in and reaches the dashboard on success', async () => {
    let loggedIn = false
    renderApp({
      entry: '/admin/login',
      handlers: {
        ...adminDataHandlers(),
        '/api/auth/me': () =>
          loggedIn ? { body: meFixture } : { status: 401, body: NOT_AUTHENTICATED },
        '/api/auth/csrf': { body: { csrfToken: 't' } },
        '/api/auth/login': () => {
          loggedIn = true
          return { body: { status: 'ok' } }
        },
      },
    })

    await screen.findByRole('button', { name: /sign in/i })
    fireEvent.change(screen.getByLabelText(/^email/i), { target: { value: 'owner@thridhalabs.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'secret' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByRole('heading', { level: 1, name: /dashboard/i })).toBeInTheDocument()
  })

  it('shows a clean error on invalid credentials', async () => {
    renderApp({
      entry: '/admin/login',
      handlers: {
        '/api/auth/csrf': { body: { csrfToken: 't' } },
        '/api/auth/login': { status: 401, body: NOT_AUTHENTICATED },
      },
    })

    await screen.findByRole('button', { name: /sign in/i })
    fireEvent.change(screen.getByLabelText(/^email/i), { target: { value: 'x@y.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'wrong' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByText(/incorrect email or password/i)).toBeInTheDocument()
  })
})

describe('admin dashboard', () => {
  it('shows metrics and quick actions', async () => {
    renderApp({ entry: '/admin', handlers: adminDataHandlers() })
    expect(await screen.findByRole('heading', { level: 1, name: /dashboard/i })).toBeInTheDocument()
    const metricsSection = await screen.findByRole('region', { name: /site overview/i })
    expect(within(metricsSection).getByText('Clients')).toBeInTheDocument()
    expect(within(metricsSection).getByText('Projects')).toBeInTheDocument()
    expect(within(metricsSection).getByText('Testimonials')).toBeInTheDocument()
    expect(within(metricsSection).getByText('Media assets')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /add project/i })).toHaveAttribute('href', '/admin/projects/new')
    expect(screen.getByRole('link', { name: /upload media/i })).toHaveAttribute('href', '/admin/media')
  })
})

describe('admin settings', () => {
  it('loads, edits and saves via PUT /api/settings', async () => {
    const { calls } = renderApp({ entry: '/admin/settings', handlers: adminDataHandlers() })
    const siteNameInput = await screen.findByLabelText(/site name/i)
    await waitFor(() => expect(siteNameInput).toHaveValue('Thridha Labs'))

    fireEvent.change(siteNameInput, { target: { value: 'Thridha X' } })
    fireEvent.click(screen.getByRole('button', { name: /save settings/i }))

    await waitFor(() => {
      const put = calls.find((c) => c.url.includes('/api/settings') && c.init?.method === 'PUT')
      expect(put).toBeTruthy()
      const body = JSON.parse(String(put!.init?.body))
      expect(body.general.site_name).toBe('Thridha X')
    })
  })

  it('exposes the maintenance toggle', async () => {
    renderApp({ entry: '/admin/settings', handlers: adminDataHandlers() })
    await screen.findByLabelText(/site name/i)
    expect(screen.getByRole('checkbox', { name: /maintenance mode/i })).toBeInTheDocument()
  })
})

describe('admin branding', () => {
  it('reloads to defaults behind a confirm dialog (branding)', async () => {
    renderApp({ entry: '/admin/branding', handlers: adminDataHandlers() })
    await screen.findByLabelText('Primary')
    const reset = screen.getByRole('button', { name: /reset branding to defaults/i })
    fireEvent.click(reset)
    expect(screen.getByRole('heading', { name: /reset branding\?/i })).toBeInTheDocument()
    const confirm = screen.getAllByRole('button', { name: /reset/i }).find((button) => button.textContent === 'Reset')
    fireEvent.click(confirm!)
    expect(await screen.findByText(/unsaved changes/i)).toBeInTheDocument()
  })
})

describe('admin media', () => {
  it('lists media assets', async () => {
    renderApp({ entry: '/admin/media', handlers: adminDataHandlers() })
    expect(await screen.findByTitle('hero.webp')).toBeInTheDocument()
  })

  it('uploads a file via POST /api/media', async () => {
    const { calls } = renderApp({ entry: '/admin/media', handlers: adminDataHandlers() })
    await screen.findByTitle('hero.webp')
    const input = screen.getByTestId('media-upload-input')
    const file = new File([new Uint8Array([1, 2, 3])], 'hero.webp', { type: 'image/webp' })
    fireEvent.change(input, { target: { files: [file] } })
    await waitFor(() => {
      const post = calls.find((c) => c.url.includes('/api/media') && c.init?.method === 'POST')
      expect(post).toBeTruthy()
      expect(post!.init?.body).toBeInstanceOf(FormData)
    })
  })

  it('deletes a media asset behind a confirm dialog', async () => {
    const { calls } = renderApp({ entry: '/admin/media', handlers: adminDataHandlers() })
    fireEvent.click(await screen.findByTitle('hero.webp'))
    fireEvent.click(await screen.findByRole('button', { name: 'Delete' }))
    const dialog = await screen.findByRole('dialog', { name: /delete this media\?/i })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete' }))
    await waitFor(() => {
      const del = calls.find((c) => c.url.includes('/api/media/m-1') && c.init?.method === 'DELETE')
      expect(del).toBeTruthy()
    })
  })

  it('hides delete actions from editors', async () => {
    renderApp({
      entry: '/admin/media',
      handlers: { ...adminDataHandlers(), '/api/auth/me': { body: editorMeFixture } },
    })
    fireEvent.click(await screen.findByTitle('hero.webp'))
    expect(
      await screen.findByText(/deleting requires an admin or owner account/i),
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument()
  })
})

describe('admin clients', () => {
  it('lists clients and supports creating one', async () => {
    const { calls } = renderApp({
      entry: '/admin/clients/new',
      handlers: adminDataHandlers(),
    })
    fireEvent.change(await screen.findByLabelText(/^name/i), { target: { value: 'Acme Co' } })
    fireEvent.click(screen.getByRole('button', { name: /create client/i }))
    await waitFor(() => {
      const post = calls.find((c) => c.url.endsWith('/api/clients') && c.init?.method === 'POST')
      expect(post).toBeTruthy()
      const body = JSON.parse(String(post!.init?.body))
      expect(body.name).toBe('Acme Co')
    })
  })

  it('hides delete for editors but keeps it for admins/owners', async () => {
    renderApp({
      entry: '/admin/clients',
      handlers: { ...adminDataHandlers(), '/api/auth/me': { body: editorMeFixture } },
    })
    expect(await screen.findByText('Acme Co')).toBeInTheDocument()
    expect(screen.queryAllByRole('button', { name: /delete/i })).toHaveLength(0)
  })

  it('shows delete for admins/owners', async () => {
    renderApp({ entry: '/admin/clients', handlers: adminDataHandlers() })
    expect(await screen.findByText('Acme Co')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /delete/i }).length).toBeGreaterThan(0)
  })
})

describe('admin projects', () => {
  it('creates a project with a chosen type', async () => {
    const { calls } = renderApp({ entry: '/admin/projects/new', handlers: adminDataHandlers() })
    fireEvent.change(await screen.findByLabelText(/project name/i), { target: { value: 'Atlas X' } })
    fireEvent.change(screen.getByLabelText(/project type/i), { target: { value: 'experiment' } })
    fireEvent.click(screen.getByRole('button', { name: /create project/i }))
    await waitFor(() => {
      const post = calls.find((c) => c.url.endsWith('/api/projects') && c.init?.method === 'POST')
      expect(post).toBeTruthy()
      const body = JSON.parse(String(post!.init?.body))
      expect(body.name).toBe('Atlas X')
      expect(body.project_type).toBe('experiment')
    })
  })

  it('hydrates the edit form', async () => {
    renderApp({ entry: '/admin/projects/p-1', handlers: adminDataHandlers() })
    await waitFor(() => expect(screen.getByLabelText(/project name/i)).toHaveValue('Atlas Engine'))
    expect(screen.getByLabelText(/^status/i)).toHaveValue('published')
  })
})

describe('admin testimonials', () => {
  it('explains the visibility rule from status/published/featured state', async () => {
    renderApp({ entry: '/admin/testimonials/new', handlers: adminDataHandlers() })
    expect(await screen.findByText(/hidden until approved/i)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/moderation status/i), { target: { value: 'approved' } })
    expect(await screen.findByText(/nowhere on the public site/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('checkbox', { name: /published/i }))
    expect(await screen.findByText(/appears on the testimonials page/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('checkbox', { name: /featured/i }))
    expect(await screen.findByText(/appears on the home page/i)).toBeInTheDocument()
  })

  it('approves a pending testimonial from the list', async () => {
    const { calls } = renderApp({
      entry: '/admin/testimonials',
      handlers: {
        ...adminDataHandlers(),
        '/api/testimonials': { body: { items: [pendingTestimonialFixture], total: 1, page: 1, page_size: 20, pages: 1 } },
      },
    })
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    await waitFor(() => {
      const patch = calls.find((c) => c.url.includes('/api/testimonials/t-pending') && c.init?.method === 'PATCH')
      expect(patch).toBeTruthy()
      const body = JSON.parse(String(patch!.init?.body))
      expect(body.status).toBe('approved')
    })
  })
})

describe('admin account', () => {
  it('shows the signed-in account and role', async () => {
    renderApp({ entry: '/admin/account', handlers: adminDataHandlers() })
    expect((await screen.findAllByText('owner@thridhalabs.com')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Owner').length).toBeGreaterThan(0)
  })
})

describe('admin brand theming', () => {
  it('applies a light preset to the admin shell and still renders the list', async () => {
    const arctic = {
      ...adminBrandingFixture,
      mode: 'light',
      theme_preset: 'arctic_white',
      colors: { primary: '#2563eb', secondary: '#0e7490', accent: '#1d4ed8', background: '#ffffff', text: '#0f172a' },
    }
    renderApp({
      entry: '/admin/testimonials',
      handlers: { ...adminDataHandlers(), '/api/public/branding': { body: arctic } },
    })

    expect(await screen.findByText('Ada Lovelace')).toBeInTheDocument()
    const root = document.documentElement
    await waitFor(() => expect(root.style.colorScheme).toBe('light'))
    expect(root.style.getPropertyValue(BRANDING_CSS_VARS.background)).toBe('#ffffff')
    expect(root.style.getPropertyValue(BRANDING_CSS_VARS.text)).toBe('#0f172a')
    expect(root.style.getPropertyValue(BRANDING_CSS_VARS.primary)).toBe('#2563eb')
  })

  it('falls back to the default dark palette when branding is unavailable', async () => {
    // Clear any inline theme left on <html> by an earlier test in this file.
    document.documentElement.removeAttribute('style')
    renderApp({
      entry: '/admin',
      handlers: {
        ...adminDataHandlers(),
        '/api/public/branding': { status: 404, body: { error: { code: 'NOT_FOUND' } } },
      },
    })
    await screen.findByRole('heading', { level: 1, name: /dashboard/i })
    // No inline branding overrides were applied; tokens.css defaults remain.
    expect(document.documentElement.style.colorScheme).toBe('')
    expect(document.documentElement.style.getPropertyValue(BRANDING_CSS_VARS.primary)).toBe('')
  })
})

describe('admin session expiry', () => {
  it('redirects to /admin/login when a data call returns 401', async () => {
    renderApp({
      entry: '/admin',
      handlers: {
        ...adminDataHandlers(),
        '/api/clients': { status: 401, body: NOT_AUTHENTICATED },
        '/api/projects': { status: 401, body: NOT_AUTHENTICATED },
        '/api/testimonials': { status: 401, body: NOT_AUTHENTICATED },
        '/api/media': { status: 401, body: NOT_AUTHENTICATED },
      },
    })
    expect(await screen.findByRole('heading', { level: 1, name: /sign in/i })).toBeInTheDocument()
  })
})
