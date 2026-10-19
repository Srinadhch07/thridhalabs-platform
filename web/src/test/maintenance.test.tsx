/** Maintenance-mode foundation tests. */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MaintenanceGuard } from '../components/layout/PublicLayout'
import { renderApp } from './helpers'
import { adminDataHandlers, settingsFixture } from './fixtures'

describe('MaintenanceGuard', () => {
  it('renders children when maintenance is disabled', () => {
    render(
      <MaintenanceGuard enabled={false}>
        <p>normal content</p>
      </MaintenanceGuard>,
    )
    expect(screen.getByText('normal content')).toBeInTheDocument()
    expect(screen.queryByText(/maintenance/i)).not.toBeInTheDocument()
  })

  it('shows the maintenance page when enabled', () => {
    render(
      <MaintenanceGuard enabled={true}>
        <p>normal content</p>
      </MaintenanceGuard>,
    )
    expect(screen.getByRole('heading', { name: /maintenance in progress/i })).toBeInTheDocument()
    expect(screen.queryByText('normal content')).not.toBeInTheDocument()
  })
})

describe('maintenance through the public layout', () => {
  it('routes public traffic to the maintenance page when maintenance is on', async () => {
    renderApp({
      entry: '/',
      handlers: {
        '/api/public/settings': { body: { ...settingsFixture, maintenance_mode: true } },
      },
    })
    expect(await screen.findByRole('heading', { name: /maintenance in progress/i })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { level: 1, name: /thridha labs/i })).not.toBeInTheDocument()
  })

  it('renders the app normally when maintenance is off', async () => {
    renderApp({ entry: '/', handlers: { '/api/public/settings': { body: settingsFixture } } })
    expect(await screen.findByRole('heading', { level: 1, name: /exploring what intelligence can become/i })).toBeInTheDocument()
  })

  it('does not apply maintenance mode to the admin area', async () => {
    renderApp({
      entry: '/admin',
      handlers: {
        ...adminDataHandlers(),
        '/api/public/settings': { body: { ...settingsFixture, maintenance_mode: true } },
      },
    })
    expect(await screen.findByRole('heading', { level: 1, name: /dashboard/i })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /maintenance in progress/i })).not.toBeInTheDocument()
  })
})