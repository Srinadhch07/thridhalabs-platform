/** SEO helpers — domain-aware canonical origin + default robots directives. */

import { afterEach, describe, expect, it } from 'vitest'
import { SITE_URL } from '../app/config/env'
import {
  absolutePageUrl,
  applyPageMeta,
  getSiteOrigin,
  projectShareImagePath,
} from '../lib/utils/seo'

function goto(path: string): void {
  window.history.pushState({}, '', path)
}

function robotsMeta(): string | null {
  return document.head.querySelector('meta[name="robots"]')?.getAttribute('content') ?? null
}

afterEach(() => {
  window.history.pushState({}, '', '/')
})

describe('canonical origin', () => {
  it('prefers the configured production origin', () => {
    expect(getSiteOrigin()).toBe(SITE_URL)
    expect(absolutePageUrl('/projects')).toBe(`${SITE_URL}/projects`)
  })

  it('normalises a path without a leading slash', () => {
    expect(absolutePageUrl('about')).toBe(`${SITE_URL}/about`)
  })

  it('builds share image URLs on the canonical origin', () => {
    expect(absolutePageUrl(projectShareImagePath('atlas engine'))).toBe(
      `${SITE_URL}/share/projects/atlas%20engine/image`,
    )
  })
})

describe('default robots directives', () => {
  it('noindexes private and verification prefixes', () => {
    for (const path of [
      '/admin',
      '/admin/projects',
      '/member',
      '/member/works/new',
      '/setup',
      '/verify-certificate/abc',
      '/verify-activity-certificate/abc',
    ]) {
      goto(path)
      const cleanup = applyPageMeta({ title: 'x' })
      expect(robotsMeta(), path).toBe('noindex, nofollow')
      cleanup()
    }
  })

  it('leaves public routes without an explicit robots directive', () => {
    for (const path of ['/', '/projects', '/projects/atlas-engine', '/members/abc']) {
      goto(path)
      const cleanup = applyPageMeta({ title: 'x' })
      expect(robotsMeta(), path).toBeNull()
      cleanup()
    }
  })

  it('honours an explicit robots override', () => {
    goto('/projects')
    const cleanup = applyPageMeta({ title: 'x', robots: 'index, follow' })
    expect(robotsMeta()).toBe('index, follow')
    cleanup()
  })
})
