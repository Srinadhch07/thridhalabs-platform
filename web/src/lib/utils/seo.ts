/**
 * SEO foundation — reusable per-page metadata.
 *
 * Focused on title / description / canonical / basic Open Graph only. Sitemap,
 * robots.txt, JSON-LD and Search Console integration belong to later phases.
 */

import { useEffect } from 'react'
import { useBranding } from '../../app/providers/BrandingProvider'
import { resolveMediaUrl } from './mediaUrl'

export interface PageMeta {
  title?: string | null
  description?: string | null
  canonical?: string | null
  ogTitle?: string | null
  ogDescription?: string | null
  ogImage?: string | null
  ogImageAlt?: string | null
  ogType?: string | null
  /** og:url — defaults to `canonical` when provided. */
  ogUrl?: string | null
  /** Document robots directive — admin routes default to `noindex, nofollow`. */
  robots?: string | null
}

interface ManagedElement {
  element: HTMLElement
  previous: string | null
}

function setMetaAttr(
  attribute: 'name' | 'property',
  key: string,
  value: string | null | undefined,
  managed: ManagedElement[],
): void {
  const selector = `meta[${attribute}="${key}"]`
  const existing = document.head.querySelector<HTMLMetaElement>(selector)
  if (!value) {
    if (existing) existing.remove()
    return
  }
  const element = existing ?? document.createElement('meta')
  element.setAttribute(attribute, key)
  element.setAttribute('content', value)
  if (!existing) document.head.appendChild(element)
  managed.push({ element, previous: existing?.getAttribute('content') ?? null })
}

function setCanonical(href: string | null | undefined, managed: ManagedElement[]): void {
  const selector = 'link[rel="canonical"]'
  const existing = document.head.querySelector<HTMLLinkElement>(selector)
  if (!href) {
    if (existing) existing.remove()
    return
  }
  const element = existing ?? document.createElement('link')
  element.setAttribute('rel', 'canonical')
  element.setAttribute('href', href)
  if (!existing) document.head.appendChild(element)
  managed.push({ element, previous: existing?.getAttribute('href') ?? null })
}

function defaultRobotsForLocation(): string | null {
  if (typeof window === 'undefined' || !window.location) return null
  if (window.location.pathname.startsWith('/admin')) return 'noindex, nofollow'
  return null
}

/** Absolute canonical URL for the current app origin + a given path. */
export function absolutePageUrl(path: string): string | null {
  if (typeof window === 'undefined' || !window.location?.origin) return null
  const normalised = path.startsWith('/') ? path : `/${path}`
  return `${window.location.origin}${normalised}`
}

/**
 * Server-generated 1200x630 social preview images (see the backend `/share`
 * routes). Kept relative so they always point at the current public origin.
 */
export function memberShareImagePath(memberId: string): string {
  return `/share/members/${encodeURIComponent(memberId)}/image`
}

export function projectShareImagePath(slug: string): string {
  return `/share/projects/${encodeURIComponent(slug)}/image`
}

export function workShareImagePath(memberId: string, slug: string): string {
  return `/share/members/${encodeURIComponent(memberId)}/works/${encodeURIComponent(slug)}/image`
}

/** Apply page metadata immediately and return a cleanup that reverts it. */
export function applyPageMeta(meta: PageMeta): () => void {
  const managed: ManagedElement[] = []
  const previousTitle = document.title

  if (meta.title) {
    document.title = meta.title
  }

  setMetaAttr('name', 'description', meta.description, managed)
  setMetaAttr('property', 'og:title', meta.ogTitle ?? meta.title, managed)
  setMetaAttr('property', 'og:description', meta.ogDescription ?? meta.description, managed)
  setMetaAttr('property', 'og:type', meta.ogType ?? 'website', managed)
  setMetaAttr('property', 'og:image', meta.ogImage, managed)
  setMetaAttr('property', 'og:image:alt', meta.ogImage ? meta.ogImageAlt : null, managed)
  setMetaAttr('property', 'og:url', meta.ogUrl ?? meta.canonical, managed)
  setMetaAttr('name', 'twitter:card', meta.ogImage ? 'summary_large_image' : null, managed)
  setMetaAttr('name', 'twitter:title', meta.ogTitle ?? meta.title, managed)
  setMetaAttr('name', 'twitter:description', meta.ogDescription ?? meta.description, managed)
  setMetaAttr('name', 'twitter:image', meta.ogImage, managed)
  setMetaAttr('name', 'twitter:image:alt', meta.ogImage ? meta.ogImageAlt : null, managed)
  const robots = meta.robots ?? defaultRobotsForLocation()
  setMetaAttr('name', 'robots', robots, managed)
  setCanonical(meta.canonical, managed)

  return () => {
    document.title = previousTitle
    for (const { element, previous } of managed) {
      if (!previous) {
        element.remove()
      } else if (element instanceof HTMLMetaElement) {
        element.setAttribute('content', previous)
      } else {
        element.setAttribute('href', previous)
      }
    }
  }
}

/** Hook that applies page metadata on mount and reverts it on unmount. */
export function usePageMeta(meta: PageMeta): void {
  useEffect(() => {
    return applyPageMeta(meta)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(meta)])
}

/** Branding OG image media id resolved through the public media route. */
export function useBrandingOgImage(): string | null {
  const { data } = useBranding()
  const id = data?.media?.og_image
  return id ? resolveMediaUrl(id, 'md') : null
}