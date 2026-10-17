/**
 * Contextual image upload — page integration.
 *
 * Verifies the admin branding, admin project gallery and member work editor
 * upload through the correct media endpoints and never fetch the whole library
 * just to open a form.
 */

import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import {
  adminDataHandlers,
  adminProjectFixture,
  mediaFixture,
  memberMeFixture,
  memberWorkFixture,
} from './fixtures'
import { renderApp, type FetchCall, type HandlerMap } from './helpers'

/** Method-aware `/api/media` stub: POST returns a single asset, GET a page. */
const mediaEndpoint: HandlerMap[string] = (_url: string, init?: RequestInit) =>
  init?.method === 'POST'
    ? { status: 201, body: mediaFixture }
    : { body: { items: [mediaFixture], total: 1, page: 1, page_size: 24, pages: 1 } }

function isPostTo(calls: FetchCall[], path: string): boolean {
  return calls.some((call) => call.url.includes(path) && call.init?.method === 'POST')
}

function isGetOf(calls: FetchCall[], path: string): boolean {
  return calls.some(
    (call) =>
      call.url.split('?')[0].endsWith(path) &&
      (!call.init?.method || call.init.method === 'GET'),
  )
}

function uploadFile(input: HTMLElement, name = 'new.webp'): void {
  fireEvent.change(input, {
    target: { files: [new File([new Uint8Array([1, 2, 3])], name, { type: 'image/webp' })] },
  })
}

describe('admin branding image uploads', () => {
  it('uploads a logo through POST /api/media and previews it', async () => {
    const { calls } = renderApp({
      entry: '/admin/branding',
      handlers: { ...adminDataHandlers(), '/api/media': mediaEndpoint },
    })

    const input = (await screen.findByLabelText('Logo (light backgrounds)')) as HTMLInputElement
    uploadFile(input)

    await waitFor(() => {
      const post = calls.find((c) => c.url.includes('/api/media') && c.init?.method === 'POST')
      expect(post).toBeTruthy()
      expect(post!.init?.body).toBeInstanceOf(FormData)
    })

    const preview = await screen.findByRole('img', { name: 'Logo (light backgrounds)' })
    expect(preview).toHaveAttribute('src', '/api/media/m-1/file?variant=thumb')
  })

  it('does not fetch the media library when the form opens', async () => {
    const { calls } = renderApp({ entry: '/admin/branding', handlers: adminDataHandlers() })

    await screen.findByLabelText('Logo (light backgrounds)')

    expect(isGetOf(calls, '/api/media')).toBe(false)
  })
})

describe('admin project image uploads', () => {
  it('loads only the referenced thumbnail preview (no library list)', async () => {
    const { calls } = renderApp({
      entry: '/admin/projects/p-1',
      handlers: {
        ...adminDataHandlers(),
        '/api/projects/p-1': { body: { ...adminProjectFixture, thumbnail_media_id: 'm-1' } },
      },
    })

    const preview = await screen.findByRole('img', { name: 'Thumbnail' })
    expect(preview).toHaveAttribute('src', '/api/media/m-1/file?variant=thumb')
    expect(isGetOf(calls, '/api/media/m-1')).toBe(true)
    expect(isGetOf(calls, '/api/media')).toBe(false)
  })

  it('adds a gallery image through POST /api/media', async () => {
    const { calls } = renderApp({
      entry: '/admin/projects/p-1',
      handlers: { ...adminDataHandlers(), '/api/media': mediaEndpoint },
    })

    const input = await screen.findByTestId('project-gallery-input')
    uploadFile(input)

    await waitFor(() => expect(isPostTo(calls, '/api/media')).toBe(true))
    await screen.findByRole('img', { name: 'Image 1' })
  })
})

describe('member work editor cover upload', () => {
  const memberSession = (overrides: HandlerMap = {}): HandlerMap => ({
    '/api/auth/csrf': { body: { csrfToken: 'test-csrf' } },
    '/api/member/csrf': { body: { csrfToken: 'test-csrf' } },
    '/api/member/me': { body: memberMeFixture },
    '/api/member/works/w-1': { body: memberWorkFixture },
    ...overrides,
  })

  it('uploads the cover through POST /api/member/media', async () => {
    const { calls } = renderApp({
      entry: '/member/works/w-1/edit',
      handlers: memberSession({
        '/api/member/media': (_url, init) =>
          init?.method === 'POST'
            ? {
                status: 201,
                body: {
                  ...mediaFixture,
                  id: 'mm-1',
                  urls: {
                    original: '/api/media/mm-1/file?variant=original',
                    thumb: '/api/media/mm-1/file?variant=thumb',
                  },
                },
              }
            : { body: { items: [], total: 0, page: 1, page_size: 24, pages: 0 } },
      }),
    })

    const input = (await screen.findByLabelText('Cover image')) as HTMLInputElement
    uploadFile(input)

    await waitFor(() => {
      const post = calls.find(
        (c) => c.url.includes('/api/member/media') && c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(post!.init?.body).toBeInstanceOf(FormData)
    })

    const preview = await screen.findByRole('img', { name: 'Cover image' })
    expect(preview).toHaveAttribute('src', '/api/media/mm-1/file?variant=thumb')
  })

  it('does not fetch the member media library when the editor opens', async () => {
    const { calls } = renderApp({
      entry: '/member/works/w-1/edit',
      handlers: memberSession(),
    })

    await screen.findByLabelText('Cover image')

    expect(isGetOf(calls, '/api/member/media')).toBe(false)
  })
})
