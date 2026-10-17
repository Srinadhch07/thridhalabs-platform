/** Home page — Phase 6 hero, section presence and data-driven behaviour. */

import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { renderApp } from './helpers'
import { clientsFixture, projectsFixture, testimonialsFixture } from './fixtures'

describe('home page without content', () => {
  it('renders the hero, intro, philosophy and CTA', async () => {
    renderApp({ entry: '/' })
    expect(await screen.findByRole('heading', { level: 1, name: /thridha labs/i })).toBeInTheDocument()
    expect(screen.getAllByText('We experiment with intelligence.').length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { name: /ideas connect/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Something interesting is being built/i })).toBeInTheDocument()
  })

  it('hides data sections when there is no content', async () => {
    renderApp({ entry: '/' })
    await waitFor(() => expect(screen.queryByText(/running, not promised/i)).not.toBeInTheDocument())
    expect(screen.queryByText(/People we build with/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/What people say/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Experiments, live in the lab/i)).not.toBeInTheDocument()
  })

  it('provides CTA links to projects and experiments', async () => {
    renderApp({ entry: '/' })
    expect(await screen.findByRole('link', { name: 'Explore the lab' })).toHaveAttribute('href', '/projects')
    expect(screen.getByRole('link', { name: 'See experiments' })).toHaveAttribute(
      'href',
      '/projects?type=experiment',
    )
    expect(screen.getByRole('link', { name: 'Enter Thridha Labs' })).toHaveAttribute('href', '/contact')
  })
})

describe('home page with content', () => {
  it('shows selected work, clients, experiments and testimonials from the APIs', async () => {
    renderApp({
      entry: '/',
      handlers: {
        '/api/public/projects': { body: projectsFixture() },
        '/api/public/clients': { body: clientsFixture() },
        '/api/public/testimonials': { body: testimonialsFixture() },
      },
    })
    expect(await screen.findByText('Running, not promised.')).toBeInTheDocument()
    expect(screen.getByText('Atlas Engine')).toBeInTheDocument()
    expect(screen.getByText('People we build with.')).toBeInTheDocument()
    expect(screen.getAllByText('Acme Co').length).toBeGreaterThan(0)
    expect(screen.getByText('What people say.')).toBeInTheDocument()
    expect(screen.getByText('A remarkable team that ships.')).toBeInTheDocument()
  })

  it('lists the technology in use from project stacks', async () => {
    renderApp({ entry: '/', handlers: { '/api/public/projects': { body: projectsFixture() } } })
    expect(await screen.findByText('Technology in use')).toBeInTheDocument()
    expect(screen.getAllByText('Python').length).toBeGreaterThan(0)
    expect(screen.getAllByText('LLMs').length).toBeGreaterThan(0)
  })

  it('ships a bedroom-lab philosophy loop, not fabricated claims', async () => {
    renderApp({ entry: '/' })
    expect((await screen.findAllByText('Build')).length).toBeGreaterThan(0)
    expect(screen.getByText('Break')).toBeInTheDocument()
    expect(screen.getByText('Learn')).toBeInTheDocument()
    expect(screen.getByText('Repeat')).toBeInTheDocument()
    expect(screen.getAllByText(/No ceremony, no roadmap theatre/i).length).toBeGreaterThan(0)
  })
})