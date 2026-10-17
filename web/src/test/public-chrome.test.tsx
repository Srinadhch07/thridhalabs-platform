/** Public chrome — Header, Navigation (mobile menu), Footer, brand. */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { CareersProvider } from '../app/providers/CareersProvider'
import { Navigation } from '../components/layout/Navigation'
import { renderApp, installFetchMock, defaultHandlers } from './helpers'

function navigationFixture() {
  const ui = (
    <CareersProvider>
      <MemoryRouter>
        <Navigation />
      </MemoryRouter>
    </CareersProvider>
  )
  render(ui)
}

describe('public navigation', () => {
  it('exposes a single primary landmark with the expected links', async () => {
    installFetchMock(defaultHandlers())
    navigationFixture()
    const nav = screen.getByRole('navigation', { name: 'Primary' })
    for (const label of ['Projects', 'Clients', 'Testimonials', 'About', 'Contact']) {
      expect(nav).toContainElement(screen.getByRole('link', { name: label }))
    }
  })

  it('toggles the mobile menu and reflects state on the trigger', async () => {
    const user = userEvent.setup()
    installFetchMock(defaultHandlers())
    navigationFixture()
    const toggle = screen.getByRole('button', { name: 'Open menu' })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')

    await user.click(toggle)
    expect(screen.getByRole('button', { name: 'Close menu' })).toHaveAttribute('aria-expanded', 'true')
    expect(document.getElementById('public-site-menu')).not.toBeNull()

    await user.click(screen.getByRole('button', { name: 'Close menu' }))
    expect(screen.getByRole('button', { name: 'Open menu' })).toHaveAttribute('aria-expanded', 'false')
  })

  it('closes the mobile menu when Escape is pressed', async () => {
    const user = userEvent.setup()
    installFetchMock(defaultHandlers())
    navigationFixture()
    await user.click(screen.getByRole('button', { name: 'Open menu' }))
    expect(screen.getByRole('button', { name: 'Close menu' })).toHaveAttribute('aria-expanded', 'true')
    await user.keyboard('{Escape}')
    expect(screen.getByRole('button', { name: 'Open menu' })).toHaveAttribute('aria-expanded', 'false')
  })
})

describe('public header + brand', () => {
  it('renders the wordmark brand, admin link and header progress bar', () => {
    renderApp({ entry: '/' })
    const brands = screen.getAllByRole('link', { name: /thridha labs/i })
    expect(brands.length).toBeGreaterThan(0)
    brands.forEach((brand) => expect(brand).toHaveAttribute('href', '/'))
    expect(screen.getByRole('link', { name: 'Admin' })).toHaveAttribute('href', '/admin')
    expect(document.querySelector('.public-header__progress')).not.toBeNull()
  })
})

describe('public footer', () => {
  it('renders brand, explore links, contact and copyright from settings', async () => {
    renderApp({ entry: '/contact' })
    // Wait for settings to load so the footer contact column is populated.
    await waitFor(() =>
      expect(screen.getAllByRole('link', { name: 'hello@thridhalabs.com' }).length).toBeGreaterThan(0),
    )
    for (const label of ['Projects', 'Clients', 'Testimonials', 'About', 'Contact']) {
      expect(screen.getAllByRole('link', { name: label }).length).toBeGreaterThan(0)
    }
    expect(screen.getByText('© 2026 Thridha Labs')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Contact' })).toBeInTheDocument()
  })

  it('omits the contact column when no channels or socials are configured', async () => {
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
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'Explore' })).not.toBeNull())
    expect(screen.queryByRole('heading', { name: 'Contact' })).not.toBeInTheDocument()
  })
})