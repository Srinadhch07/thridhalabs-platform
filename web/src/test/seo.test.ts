/** SEO helpers — domain-aware canonical origin + default robots directives. */

import { afterEach, describe, expect, it } from 'vitest'
import { SITE_URL } from '../app/config/env'
import {
  absolutePageUrl,
  applyPageMeta,
  getSiteOrigin,
  projectShareImagePath,
  shareUrl,
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

describe('share url (never null)', () => {
  it('uses the canonical origin when available', () => {
    expect(shareUrl('/members/THL-M-1')).toBe(`${SITE_URL}/members/THL-M-1`)
  })

  it('always returns an absolute url and normalises the path', () => {
    expect(shareUrl('projects')).toBe(`${SITE_URL}/projects`)
    // Unlike absolutePageUrl, it is never null — sharing must always work.
    expect(shareUrl('/x')).not.toBeNull()
    expect(shareUrl('/x')).toMatch(/^https?:\/\//)
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

describe('default og image fallback', () => {
  it('uses page-specific image when provided', () => {
    goto('/')
    const cleanup = applyPageMeta({
      title: 'x',
      ogImage: 'https://example.com/custom.png',
      ogImageAlt: 'Custom',
    })
    const ogImage = document.head.querySelector('meta[property="og:image"]')?.getAttribute('content')
    const twitterImage = document.head.querySelector('meta[name="twitter:image"]')?.getAttribute('content')
    expect(ogImage).toBe('https://example.com/custom.png')
    expect(twitterImage).toBe('https://example.com/custom.png')
    cleanup()
  })
})
