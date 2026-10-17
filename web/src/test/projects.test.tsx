/** Projects page — Phase 6 filter behaviour, entries meta, empty and error states. */

import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { renderApp } from './helpers'
import { projectsFixture } from './fixtures'

describe('projects index', () => {
  it('lists projects with counts and filter pills', async () => {
    renderApp({ entry: '/projects', handlers: { '/api/public/projects': { body: projectsFixture() } } })
    expect(await screen.findByRole('heading', { level: 1, name: /selected work and experiments/i })).toBeInTheDocument()
    expect(await screen.findByText(/01 entries on file/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'View project: Atlas Engine' })).toHaveAttribute(
      'href',
      '/projects/atlas-engine',
    )
    expect(screen.getByRole('button', { name: /All/ })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: /Client work/ })).toHaveAttribute('aria-pressed', 'false')
  })

  it('filters projects by the type query parameter', async () => {
    renderApp({ entry: '/projects?type=experiment', handlers: { '/api/public/projects': { body: projectsFixture() } } })
    expect(await screen.findByText('Atlas Engine')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Experiments/ })).toHaveAttribute('aria-pressed', 'true')
  })

  it('shows an empty category state when the filter matches nothing', async () => {
    renderApp({ entry: '/projects?type=product', handlers: { '/api/public/projects': { body: projectsFixture() } } })
    expect(await screen.findByText(/No products in this category/)).toBeInTheDocument()
    expect(screen.queryByText('Atlas Engine')).not.toBeInTheDocument()
  })

  it('shows an empty state when the API returns nothing', async () => {
    renderApp({ entry: '/projects' })
    expect(await screen.findByText('No projects yet')).toBeInTheDocument()
  })

  it('shows a retryable error state on failure', async () => {
    renderApp({
      entry: '/projects',
      handlers: {
        '/api/public/projects': { status: 500, body: { error: { code: 'INTERNAL', message: 'boom' } } },
      },
    })
    expect(await screen.findByRole('heading', { name: 'Unable to load projects' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })

  it('still exposes project filenames via project cards without duplicating the name', async () => {
    renderApp({ entry: '/projects', handlers: { '/api/public/projects': { body: projectsFixture() } } })
    await screen.findByRole('link', { name: 'View project: Atlas Engine' })
    const matches = screen.getAllByText('Atlas Engine')
    expect(matches.length).toBe(1)
  })
})

describe('projects index seo', () => {
  it('sets the projects page title', async () => {
    renderApp({ entry: '/projects' })
    await waitFor(() => expect(document.title).toBe('Projects — Thridha Labs'))
  })
})