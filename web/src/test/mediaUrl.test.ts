/** Media URL resolution tests. */

import { describe, expect, it } from 'vitest'
import { absolutize, resolveMediaUrl } from '../lib/utils/mediaUrl'
import type { Media } from '../types/media'

function media(overrides: Partial<Media>): Media {
  return {
    id: 'm-1',
    original_name: 'photo.jpg',
    format: 'jpg',
    mime_type: 'image/jpeg',
    media_type: 'image',
    size_bytes: 123,
    width: 100,
    height: 100,
    checksum: 'abc',
    storage_mode: 'local',
    variants: [],
    urls: {
      original: '/api/media/m-1/file?variant=original',
      thumb: '/api/media/m-1/file?variant=thumb',
    },
    created_by: 'u-1',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('resolveMediaUrl', () => {
  it('returns the requested variant path for a media record', () => {
    expect(resolveMediaUrl(media({}), 'thumb')).toBe('/api/media/m-1/file?variant=thumb')
  })

  it('defaults to the original variant', () => {
    expect(resolveMediaUrl(media({}))).toBe('/api/media/m-1/file?variant=original')
  })

  it('returns null for missing media or missing variants', () => {
    expect(resolveMediaUrl(null)).toBeNull()
    expect(resolveMediaUrl(undefined)).toBeNull()
    expect(resolveMediaUrl('')).toBeNull()
    expect(resolveMediaUrl('   ')).toBeNull()
    expect(resolveMediaUrl(media({ urls: {} }))).toBeNull()
  })

  it('resolves a bare media id through the public delivery route', () => {
    expect(resolveMediaUrl('m-1', 'thumb')).toBe('/api/public/media/m-1?variant=thumb')
  })

  it('defaults a bare media id to the original variant and encodes segments', () => {
    expect(resolveMediaUrl('m-1')).toBe('/api/public/media/m-1?variant=original')
  })
})

describe('absolutize', () => {
  it('preserves absolute http(s) URLs, data URIs and protocol-relative URLs', () => {
    expect(absolutize('https://cdn.example.com/a.png')).toBe('https://cdn.example.com/a.png')
    expect(absolutize('//cdn.example.com/a.png')).toBe('//cdn.example.com/a.png')
    expect(absolutize('data:image/png;base64,AAAA')).toBe('data:image/png;base64,AAAA')
  })

  it('returns null for empty input', () => {
    expect(absolutize(null)).toBeNull()
    expect(absolutize('')).toBeNull()
  })
})