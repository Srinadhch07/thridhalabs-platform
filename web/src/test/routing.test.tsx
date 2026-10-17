/** Routing architecture tests — public routes, admin namespace, 404, SEO/a11y. */

import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { renderApp } from './helpers'
import { adminDataHandlers, clientsFixture, projectDetailsFixture, projectsFixture, testimonialsFixture } from './fixtures'

describe('public routing', () => {
  it('renders the home page at /', async () => {
    renderApp({ entry: '/' })
    expect(await screen.findByRole('heading', { level: 1, name: /thridha labs/i })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Primary' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Skip to main content' })).toBeInTheDocument()
  })

  it('shows the projects page at /projects', async () => {
    renderApp({ entry: '/projects', handlers: { '/api/public/projects': { body: projectsFixture() } } })
    expect(await screen.findByRole('heading', { level: 1, name: /selected work/i })).toBeInTheDocument()
    expect(await screen.findByText('Atlas Engine')).toBeInTheDocument()
  })

  it('shows an empty state when /projects has no content', async () => {
    renderApp({ entry: '/projects' })
    expect(await screen.findByRole('heading', { level: 1, name: /selected work/i })).toBeInTheDocument()
    expect(await screen.findByText('No projects yet')).toBeInTheDocument()
  })

  it('renders the project detail page at /projects/:slug', async () => {
    renderApp({
      entry: '/projects/atlas-engine',
      handlers: { '/api/public/projects/atlas-engine': { body: projectDetailsFixture } },
    })
    expect(await screen.findByRole('heading', { level: 1, name: 'Atlas Engine' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /back to projects/i })).toBeInTheDocument()
  })

  it('shows a not-found state for an unknown project slug', async () => {
    renderApp({
      entry: '/projects/does-not-exist',
      handlers: {
        '/api/public/projects/does-not-exist': {
          status: 404,
          body: { error: { code: 'NOT_FOUND', message: 'Not found' } },
        },
      },
    })
    expect(await screen.findByText('Page not found')).toBeInTheDocument()
  })

  it('renders the clients page at /clients', async () => {
    renderApp({ entry: '/clients', handlers: { '/api/public/clients': { body: clientsFixture() } } })
    expect(await screen.findByRole('heading', { level: 1, name: /people we work with/i })).toBeInTheDocument()
    expect(await screen.findByText('Acme Co')).toBeInTheDocument()
  })

  it('renders the testimonials page at /testimonials', async () => {
    renderApp({
      entry: '/testimonials',
      handlers: { '/api/public/testimonials': { body: testimonialsFixture() } },
    })
    expect(await screen.findByRole('heading', { level: 1, name: /what people say/i })).toBeInTheDocument()
    expect((await screen.findAllByText('A remarkable team that ships.')).length).toBeGreaterThan(0)
  })

  it('renders the about page at /about', async () => {
    renderApp({ entry: '/about' })
    expect(await screen.findByRole('heading', { level: 1, name: /About Thridha Labs/i })).toBeInTheDocument()
  })

  it('renders the contact page at /contact', async () => {
    renderApp({ entry: '/contact' })
    expect(await screen.findByRole('heading', { level: 1, name: /get in touch/i })).toBeInTheDocument()
    expect((await screen.findAllByRole('link', { name: 'hello@thridhalabs.com' })).length).toBeGreaterThan(0)
  })
})

describe('not found handling', () => {
  it('renders the application 404 page for unknown routes', async () => {
    renderApp({ entry: '/this-route-does-not-exist' })
    expect(await screen.findByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /back to home/i })).toBeInTheDocument()
  })

  it('renders the 404 page at the explicit /404 route', async () => {
    renderApp({ entry: '/404' })
    expect(await screen.findByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
  })
})

describe('admin routing', () => {
  it('renders the admin dashboard at /admin without public navigation', async () => {
    renderApp({ entry: '/admin', handlers: adminDataHandlers() })
    expect(await screen.findByRole('heading', { level: 1, name: /dashboard/i })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Admin' })).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Primary' })).not.toBeInTheDocument()
  })

  it('redirects unauthenticated users from /admin to /admin/login', async () => {
    renderApp({ entry: '/admin' })
    expect(await screen.findByRole('heading', { level: 1, name: /sign in/i })).toBeInTheDocument()
  })

  it('renders the admin sign-in form at /admin/login', async () => {
    renderApp({ entry: '/admin/login' })
    expect(await screen.findByRole('heading', { level: 1, name: /sign in/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  })

  it('redirects an authenticated user away from /admin/login to /admin', async () => {
    renderApp({ entry: '/admin/login', handlers: adminDataHandlers() })
    expect(await screen.findByRole('heading', { level: 1, name: /dashboard/i })).toBeInTheDocument()
  })

  it('renders a not-found state for unknown admin sections', async () => {
    renderApp({ entry: '/admin/unknown-section', handlers: adminDataHandlers() })
    expect(await screen.findByText('Admin section not found')).toBeInTheDocument()
  })
})

describe('seo + accessibility foundation', () => {
  it('sets a meaningful page title', async () => {
    renderApp({ entry: '/projects' })
    await waitFor(() =>
      expect(document.title).toBe('Projects — Thridha Labs'),
    )
  })

  it('provides a skip link targeting main content', async () => {
    renderApp({ entry: '/' })
    const skip = await screen.findByRole('link', { name: 'Skip to main content' })
    expect(skip).toHaveAttribute('href', '#main-content')
  })
})