/**
 * Single utility for resolving media URLs.
 *
 * Backend media records carry variant URLs like `/api/media/{id}/file?variant=x`
 * (relative to the API origin), and future S3-backed URLs are absolute http(s).
 * Components must never concatenate media paths themselves — go through
 * `resolveMediaUrl`.
 */

import { API_BASE } from '../../app/config/env'

export interface MediaLike {
  urls: Record<string, string>
}

function apiOrigin(): string {
  if (/^https?:\/\//i.test(API_BASE)) {
    try {
      return new URL(API_BASE).origin
    } catch {
      return ''
    }
  }
  return ''
}

function resolvePath(url: string): string {
  if (/^https?:\/\//i.test(url) || url.startsWith('//') || url.startsWith('data:') || url.startsWith('blob:')) {
    return url
  }
  if (!url.startsWith('/')) return url
  return `${apiOrigin()}${url}`
}

/**
 * Default branding asset (thridhalabs_logo).
 */
export function getDefaultLogoUrl(): string {
  return resolvePath('/branding/default/logo.png')
}

/** Turn any backend/raw media path (or absolute URL) into a usable URL. */
export function absolutize(url: string | null | undefined): string | null {
  if (!url) return null
  return resolvePath(url)
}

/**
 * Resolve a media variant URL from a media record (or null when unavailable).
 *
 * Accepts either a stored media record (admin context — its `urls` map points
 * at the authenticated admin route) or a bare media id string (public
 * context — always routed through the unauthenticated public media delivery
 * endpoint).
 */
export function resolveMediaUrl(
  media: MediaLike | string | null | undefined,
  variant: string = 'original',
): string | null {
  if (!media) return null
  if (typeof media === 'string') {
    const id = media.trim()
    if (!id) return null
    return resolvePath(`/api/public/media/${encodeURIComponent(id)}?variant=${encodeURIComponent(variant)}`)
  }
  const url = media.urls?.[variant]
  if (!url) return null
  return resolvePath(url)
}