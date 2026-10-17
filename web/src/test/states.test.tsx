/** Reusable UI state components: loading, empty, error, not-found, boundary. */

import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { ErrorBoundary } from '../components/ui/ErrorBoundary'
import { ErrorState } from '../components/ui/ErrorState'
import { EmptyState } from '../components/ui/EmptyState'
import { NotFoundState } from '../components/ui/NotFoundState'
import { PageLoader } from '../components/ui/PageLoader'

describe('PageLoader', () => {
  it('announces loading via a status role with a friendly label', () => {
    render(<PageLoader label="Loading site" />)
    const region = screen.getByRole('status')
    expect(region).toHaveAttribute('aria-live', 'polite')
    expect(screen.getByText('Loading site')).toBeInTheDocument()
  })
})

describe('EmptyState', () => {
  it('renders the empty title', () => {
    render(<EmptyState title="No projects yet" />)
    expect(screen.getByRole('heading', { name: 'No projects yet' })).toBeInTheDocument()
  })
})

describe('NotFoundState', () => {
  it('renders a 404 heading and a recovery link', () => {
    render(
      <MemoryRouter>
        <NotFoundState />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /back to home/i })).toBeInTheDocument()
  })
})

describe('ErrorState', () => {
  it('renders a safe message and does not leak raw error internals', () => {
    const raw = new Error('secret internal stack: at Function.<anonymous>:1:1')
    render(<ErrorState title="Loading failed" error={raw} />)
    expect(screen.getByRole('heading', { name: 'Loading failed' })).toBeInTheDocument()
    expect(screen.getByText('Please try again later.')).toBeInTheDocument()
    expect(screen.queryByText(/secret internal stack/)).not.toBeInTheDocument()
  })

  it('renders the retry control when an onRetry handler is provided', () => {
    const onRetry = vi.fn()
    render(<ErrorState title="Loading failed" message="something happened" onRetry={onRetry} />)
    screen.getByRole('button', { name: 'Try again' }).click()
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('passes through an already-safe message string', () => {
    render(<ErrorState title="Loading failed" message="The project could not be loaded." />)
    expect(screen.getByText('The project could not be loaded.')).toBeInTheDocument()
  })
})

describe('ErrorBoundary', () => {
  function Exploder(): never {
    throw new Error('boom-internal')
  }

  it('shows the fallback and hides the original error from users', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary>
        <Exploder />
      </ErrorBoundary>,
    )
    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Something went wrong' })).toBeInTheDocument()
    expect(screen.queryByText(/boom-internal/)).not.toBeInTheDocument()
    spy.mockRestore()
  })

  it('renders children normally when nothing throws', () => {
    render(
      <ErrorBoundary>
        <p>fine</p>
      </ErrorBoundary>,
    )
    expect(screen.getByText('fine')).toBeInTheDocument()
  })
})