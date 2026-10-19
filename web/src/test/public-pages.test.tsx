/** Clients, testimonials, about and contact pages — Phase 6 data + narrative content. */

import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { renderApp } from './helpers'
import { clientsFixture, testimonialsFixture } from './fixtures'

describe('clients page', () => {
  it('lists clients from the API with monogram and project count', async () => {
    renderApp({ entry: '/clients', handlers: { '/api/public/clients': { body: clientsFixture() } } })
    expect(await screen.findByRole('heading', { level: 1, name: /people we work with/i })).toBeInTheDocument()
    expect(await screen.findByText('Acme Co')).toBeInTheDocument()
    expect(await screen.findByText(/01 entries on file/)).toBeInTheDocument()
    expect(screen.getByText('0 projects')).toBeInTheDocument()
  })

  it('shows an empty state when no clients exist', async () => {
    renderApp({ entry: '/clients' })
    expect(await screen.findByText('No clients yet')).toBeInTheDocument()
  })

  it('shows a retryable error state on failure', async () => {
    renderApp({
      entry: '/clients',
      handlers: { '/api/public/clients': { status: 500, body: { error: { code: 'INTERNAL', message: 'boom' } } } },
    })
    expect(await screen.findByRole('heading', { name: 'Unable to load clients' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
})

describe('testimonials page', () => {
  it('renders quotes with attribution and star rating', async () => {
    renderApp({
      entry: '/testimonials',
      handlers: { '/api/public/testimonials': { body: testimonialsFixture() } },
    })
    expect(await screen.findByRole('heading', { level: 1, name: /what people say/i })).toBeInTheDocument()
    expect(await screen.findByText('A remarkable team that ships.')).toBeInTheDocument()
    expect(screen.getByText('Ada Lovelace')).toBeInTheDocument()
    expect(await screen.findByText(/01 signals on file/)).toBeInTheDocument()
    expect(screen.getByText('Rated 5 out of 5')).toBeInTheDocument()
  })

  it('shows an empty state when no testimonials exist', async () => {
    renderApp({ entry: '/testimonials' })
    expect(await screen.findByText('No testimonials yet')).toBeInTheDocument()
  })

  it('shows a retryable error state on failure', async () => {
    renderApp({
      entry: '/testimonials',
      handlers: {
        '/api/public/testimonials': { status: 500, body: { error: { code: 'INTERNAL', message: 'boom' } } },
      },
    })
    expect(await screen.findByRole('heading', { name: 'Unable to load testimonials' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
})

describe('about page', () => {
  it('renders settings-driven identity and the operating loop', async () => {
    renderApp({ entry: '/about' })
    expect(await screen.findByRole('heading', { level: 1, name: /About Thridha Labs/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Build. Break. Learn. Repeat.' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Function before gloss.' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'See the work' })).toHaveAttribute('href', '/projects')
    expect(screen.getByRole('link', { name: 'Bring a question' })).toHaveAttribute('href', '/contact')
  })
})

describe('contact page', () => {
  it('renders configured channels and social links', async () => {
    renderApp({ entry: '/contact' })
    expect(
      await screen.findByRole('heading', { level: 1, name: /have something worth building/i }),
    ).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Email' })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'hello@thridhalabs.com' }).length).toBeGreaterThan(0)
  })

  it('falls back gracefully when no channels are configured', async () => {
    renderApp({
      entry: '/contact',
      handlers: {
        '/api/public/settings': {
          body: {
            general: {
              site_name: 'Thridha Labs',
              tagline: 'We experiment with intelligence.',
              description: 'AI, software and ideas turned into things people can actually use.',
            },
            contact: { contact_email: null, contact_phone: null, whatsapp: null, address: null },
            social: { urls: {} },
            footer: { copyright_text: '© 2026 Thridha Labs' },
            seo: { seo_title: 'Thridha Labs', seo_description: 'A tech lab', seo_keywords: [] },
          },
        },
      },
    })
    expect(await screen.findByText(/Contact channels are not configured yet/i)).toBeInTheDocument()
  })
})

describe('phase 6 page titles', () => {
  it('sets distinct titles for the public pages', async () => {
    renderApp({ entry: '/clients' })
    await waitFor(() => expect(document.title).toBe('Clients — Thridha Labs'))
  })

  it('sets the testimonials page title', async () => {
    renderApp({ entry: '/testimonials' })
    await waitFor(() => expect(document.title).toBe('Testimonials — Thridha Labs'))
  })

  it('sets the about page title', async () => {
    renderApp({ entry: '/about' })
    await waitFor(() => expect(document.title).toBe('About — Thridha Labs'))
  })

  it('sets the contact page title', async () => {
    renderApp({ entry: '/contact' })
    await waitFor(() => expect(document.title).toBe('Contact — Thridha Labs'))
  })
})