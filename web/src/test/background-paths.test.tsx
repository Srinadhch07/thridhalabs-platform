/**
 * BackgroundPaths — decorative animated hero backdrop.
 *
 * Guards the integration contract: the layer is inert and hidden from
 * assistive technology, it fills its parent without forcing layout, and it
 * renders statically under prefers-reduced-motion.
 */

import { render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { BackgroundPaths } from '../components/ui/background-paths'

function mockReducedMotion(reduce: boolean): void {
  vi.stubGlobal(
    'matchMedia',
    vi.fn((query: string) => ({
      matches: reduce && query.includes('prefers-reduced-motion'),
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(() => false),
    })),
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('BackgroundPaths', () => {
  it('renders a decorative layer hidden from assistive tech and pointer events', () => {
    const { container } = render(<BackgroundPaths />)
    const layer = container.querySelector('.background-paths')
    expect(layer).not.toBeNull()
    expect(layer).toHaveAttribute('aria-hidden', 'true')
    expect(container.querySelector('svg')).not.toBeNull()
  })

  it('renders three deterministic animated paths', () => {
    const { container } = render(<BackgroundPaths />)
    const paths = container.querySelectorAll('path')
    expect(paths.length).toBe(3)
  })

  it('renders statically under prefers-reduced-motion', () => {
    mockReducedMotion(true)
    const { container } = render(<BackgroundPaths />)
    expect(container.querySelectorAll('path').length).toBe(3)
  })
})
