/** Phase 8 — public media rendering + SEO metadata + JSON-LD. */

import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { renderApp } from './helpers'
import {
  brandingFixture,
  clientsFixture,
  projectDetailsFixture,
  projectsFixture,
  testimonialsFixture,
} from './fixtures'

function metaContent(selector: string): string | null {
  return document.head.querySelector(selector)?.getAttribute('content') ?? null
}

function jsonLdBlocks(): Array<Record<string, unknown>> {
  return [...document.head.querySelectorAll('script[type="application/ld+json"]')].map((el) =>
    JSON.parse(el.textContent ?? '{}'),
  )
}

describe('public media rendering', () => {
  it('renders the project thumbnail through the public media route', async () => {
    const withThumb = projectsFixture()
    withThumb.items[0] = { ...withThumb.items[0], thumbnail_media_id: 'm-1' }
    renderApp({ entry: '/projects', handlers: { '/api/public/projects': { body: withThumb } } })
    const img = await screen.findByRole('img', { name: /atlas engine visual/i })
    // The fixture project is featured, so the featured card requests the lg variant.
    expect(img).toHaveAttribute('src', '/api/public/media/m-1?variant=lg')
  })

  it('falls back to the placeholder when the project has no media', async () => {
    renderApp({ entry: '/projects', handlers: { '/api/public/projects': { body: projectsFixture() } } })
    await screen.findByText('Atlas Engine')
    expect(screen.queryByRole('img', { name: /atlas engine visual/i })).not.toBeInTheDocument()
  })

  it('renders the client logo and cover when configured', async () => {
    const withMedia = clientsFixture()
    withMedia.items[0] = {
      ...withMedia.items[0],
      logo_media_id: 'm-logo',
      featured_image_media_id: 'm-cover',
    }
    renderApp({ entry: '/clients', handlers: { '/api/public/clients': { body: withMedia } } })
    expect(await screen.findByRole('img', { name: /acme co logo/i })).toHaveAttribute(
      'src',
      '/api/public/media/m-logo?variant=thumb',
    )
    expect(screen.getByRole('img', { name: /acme co featured visual/i })).toHaveAttribute(
      'src',
      '/api/public/media/m-cover?variant=md',
    )
  })

  it('renders testimonial avatars when configured', async () => {
    const withAvatar = testimonialsFixture()
    withAvatar.items[0] = { ...withAvatar.items[0], profile_image_media_id: 'm-face' }
    renderApp({ entry: '/testimonials', handlers: { '/api/public/testimonials': { body: withAvatar } } })
    expect(await screen.findByRole('img', { name: /ada lovelace portrait/i })).toHaveAttribute(
      'src',
      '/api/public/media/m-face?variant=thumb',
    )
  })

  it('uses the branding logo in the header when configured', async () => {
    renderApp({
      entry: '/',
      handlers: {
        '/api/public/branding': {
          body: { ...brandingFixture, media: { ...brandingFixture.media, logo: 'm-brand' } },
        },
      },
    })
    expect(await screen.findByRole('img', { name: /logo/i })).toHaveAttribute(
      'src',
      '/api/public/media/m-brand?variant=thumb',
    )
  })
})

describe('canonical urls and open graph', () => {
  it('sets canonical + og:url on listing pages', async () => {
    renderApp({ entry: '/projects' })
    await screen.findByRole('heading', { level: 1, name: /selected work/i })
    await waitFor(() => {
      const canonical = document.head.querySelector('link[rel="canonical"]')
      expect(canonical?.getAttribute('href')).toMatch(/\/projects$/)
      expect(metaContent('meta[property="og:url"]')).toMatch(/\/projects$/)
    })
  })

  it('sets project-specific metadata on the detail page', async () => {
    renderApp({
      entry: '/projects/atlas-engine',
      handlers: {
        '/api/public/projects/atlas-engine': {
          body: { ...projectDetailsFixture, thumbnail_media_id: 'm-2' },
        },
      },
    })
    await screen.findByRole('heading', { level: 1, name: 'Atlas Engine' })
    await waitFor(() => {
      expect(document.head.querySelector('link[rel="canonical"]')?.getAttribute('href')).toMatch(
        /\/projects\/atlas-engine$/,
      )
      // Social previews use the generated share card even when a thumbnail exists.
      expect(metaContent('meta[property="og:image"]')).toBe(
        `${window.location.origin}/share/projects/atlas-engine/image`,
      )
    })
  })

  it('falls back to the branding OG image when content has none', async () => {
    renderApp({
      entry: '/about',
      handlers: {
        '/api/public/branding': {
          body: { ...brandingFixture, media: { ...brandingFixture.media, og_image: 'm-og' } },
        },
      },
    })
    await screen.findByRole('heading', { level: 1, name: /about thridha labs/i })
    await waitFor(() => {
      expect(metaContent('meta[property="og:image"]')).toBe('/api/public/media/m-og?variant=md')
    })
  })

  it('marks the 404 page as noindex', async () => {
    renderApp({ entry: '/no-such-route-here' })
    await screen.findByRole('heading', { name: 'Page not found' })
    await waitFor(() => {
      expect(metaContent('meta[name="robots"]')).toBe('noindex, nofollow')
    })
  })
})

describe('json-ld', () => {
  it('emits Organization + WebSite blocks on the home page', async () => {
    renderApp({ entry: '/' })
    await screen.findByRole('heading', { level: 1, name: /thridha labs/i })
    await waitFor(() => {
      const types = jsonLdBlocks().map((block) => block['@type'])
      expect(types).toContain('Organization')
      expect(types).toContain('WebSite')
    })
    const org = jsonLdBlocks().find((block) => block['@type'] === 'Organization')
    expect(org?.name).toBe('Thridha Labs')
  })

  it('emits a CreativeWork block on the project detail page', async () => {
    renderApp({
      entry: '/projects/atlas-engine',
      handlers: {
        '/api/public/projects/atlas-engine': {
          body: { ...projectDetailsFixture, thumbnail_media_id: 'm-2' },
        },
      },
    })
    await screen.findByRole('heading', { level: 1, name: 'Atlas Engine' })
    await waitFor(() => {
      const work = jsonLdBlocks().find((block) => block['@type'] === 'CreativeWork')
      expect(work?.name).toBe('Atlas Engine')
      expect(work?.image).toBe('/api/public/media/m-2?variant=md')
    })
  })
})
