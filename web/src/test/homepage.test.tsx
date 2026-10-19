/**
 * Home page — Swiss editorial hero, section presence and data-driven behaviour.
 *
 * The hero was redesigned (oversized editorial headline + animated
 * BackgroundPaths backdrop + concise CTAs). Data sections remain driven by the
 * same public APIs and hide themselves when there is no content.
 */

import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { renderApp } from './helpers'
import { clientsFixture, projectsFixture, testimonialsFixture } from './fixtures'

describe('home page without content', () => {
  it('renders the cosmic editorial hero, practice and closing invitation', async () => {
    renderApp({ entry: '/' })
    expect(
      await screen.findByRole('heading', { level: 1, name: /exploring what intelligence can become/i }),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /an ai-first lab that experiments, builds and delivers/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /have an idea worth experimenting on/i })).toBeInTheDocument()
  })

  it('hides data sections when there is no content', async () => {
    renderApp({ entry: '/' })
    await waitFor(() => expect(screen.queryByText(/things we've built/i)).not.toBeInTheDocument())
    expect(screen.queryByText(/People we build with/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/What people say/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Technology in use/i)).not.toBeInTheDocument()
  })

  it('provides hero and closing CTA links to projects and contact', async () => {
    renderApp({ entry: '/' })
    const experimentLinks = await screen.findAllByRole('link', { name: 'Explore our experiments' })
    experimentLinks.forEach((link) => expect(link).toHaveAttribute('href', '/projects?type=experiment'))
    const buildLinks = screen.getAllByRole('link', { name: /see what we're building/i })
    buildLinks.forEach((link) => expect(link).toHaveAttribute('href', '/projects'))
    const projectLinks = screen.getAllByRole('link', { name: 'Start a project' })
    projectLinks.forEach((link) => expect(link).toHaveAttribute('href', '/contact'))
  })

  it('renders the cosmic field as a decorative hidden layer', async () => {
    renderApp({ entry: '/' })
    await screen.findByRole('heading', { level: 1, name: /exploring what intelligence can become/i })
    const backdrop = document.querySelector('.cosmic-field')
    expect(backdrop).not.toBeNull()
    expect(backdrop).toHaveAttribute('aria-hidden', 'true')
  })
})

describe('home page with content', () => {
  it('shows selected work, clients and testimonials from the APIs', async () => {
    renderApp({
      entry: '/',
      handlers: {
        '/api/public/projects': { body: projectsFixture() },
        '/api/public/clients': { body: clientsFixture() },
        '/api/public/testimonials': { body: testimonialsFixture() },
      },
    })
    expect(await screen.findByText("Things we've built, running now.")).toBeInTheDocument()
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
})
