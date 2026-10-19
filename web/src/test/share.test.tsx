/**
 * Share actions + social metadata.
 *
 * The backend serves the crawler-readable Open Graph documents (see the
 * `/share/...` routes); the frontend mirrors the same canonical URL and the
 * server-generated preview image, and provides native share / copy link /
 * direct share controls that never fall back to an admin URL.
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ShareActions } from '../components/public/ShareActions'
import { SITE_URL } from '../app/config/env'
import { publicMemberFixture } from './fixtures'
import { renderApp } from './helpers'

const MEMBER_ID = publicMemberFixture.member_id
const URL = `http://localhost:3000/members/${MEMBER_ID}`
const ENCODED = encodeURIComponent(URL)

/**
 * jsdom already defines `navigator.clipboard` (with a real async writeText),
 * so a plain per-instance override is shadowed. Replace the whole `navigator`
 * global instead; the shared test setup restores it via `unstubAllGlobals`.
 */
function stubNavigator(props: Record<string, unknown>) {
  const fake = Object.create(window.navigator) as Navigator
  for (const [key, value] of Object.entries(props)) {
    Object.defineProperty(fake, key, { configurable: true, writable: true, value })
  }
  vi.stubGlobal('navigator', fake)
}

function stubClipboard(impl: () => Promise<void>) {
  stubNavigator({ clipboard: { writeText: vi.fn(impl) } })
}

function stubNativeShare(impl: (...args: unknown[]) => Promise<void>) {
  stubNavigator({ share: vi.fn(impl) })
}

describe('ShareActions', () => {
  it('copies the canonical link and confirms success', async () => {
    const user = userEvent.setup()
    stubClipboard(() => Promise.resolve())
    render(<ShareActions url={URL} title="Ada Lovelace — Thridha Labs" />)

    await user.click(screen.getByRole('button', { name: /copy link/i }))

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(URL)
    expect(await screen.findByText(/link copied/i)).toBeInTheDocument()
  })

  it('reports a copy failure without throwing', async () => {
    const user = userEvent.setup()
    stubClipboard(() => Promise.reject(new Error('denied')))
    render(<ShareActions url={URL} title="Ada Lovelace — Thridha Labs" />)

    await user.click(screen.getByRole('button', { name: /copy link/i }))

    expect(await screen.findByText(/couldn't copy/i)).toBeInTheDocument()
  })

  it('offers a native share button when the device supports it', async () => {
    const user = userEvent.setup()
    stubNativeShare(() => Promise.resolve())
    render(<ShareActions url={URL} title="Ada Lovelace — Thridha Labs" text="Bio" />)

    const share = await screen.findByRole('button', { name: /^share$/i })
    await user.click(share)

    expect(navigator.share).toHaveBeenCalledWith({
      title: 'Ada Lovelace — Thridha Labs',
      text: 'Bio',
      url: URL,
    })
  })

  it('hides native share when unavailable and exposes a copy option', () => {
    stubNavigator({ share: undefined })
    render(<ShareActions url={URL} title="Ada Lovelace — Thridha Labs" />)
    expect(screen.queryByRole('button', { name: /^share$/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /copy link/i })).toBeInTheDocument()
  })

  it('shares only the canonical URL through direct targets', () => {
    render(<ShareActions url={URL} title="Ada Lovelace — Thridha Labs" />)

    const x = screen.getByRole('link', { name: /share on x/i })
    expect(x.getAttribute('href')).toContain(ENCODED)
    expect(screen.getByRole('link', { name: /linkedin/i }).getAttribute('href')).toContain(ENCODED)
    expect(screen.getByRole('link', { name: /facebook/i }).getAttribute('href')).toContain(ENCODED)
    expect(screen.getByRole('link', { name: /whatsapp/i }).getAttribute('href')).toContain(ENCODED)
    expect(screen.getByRole('link', { name: /email/i }).getAttribute('href')).toContain(ENCODED)
    expect(x.getAttribute('href')).not.toContain('/admin')
  })
})

describe('member page sharing', () => {
  it('renders share controls and mirrors the server preview image', async () => {
    renderApp({
      entry: `/members/${MEMBER_ID}`,
      handlers: {
        [`/api/public/members/${MEMBER_ID}`]: { body: publicMemberFixture },
      },
    })

    expect(await screen.findByRole('heading', { level: 1, name: 'Ada Lovelace' })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /copy link/i })).toBeInTheDocument()

    const canonical = `${SITE_URL}/members/${MEMBER_ID}`
    const x = screen.getByRole('link', { name: /share on x/i })
    expect(x.getAttribute('href')).toContain(encodeURIComponent(canonical))

    await waitFor(() => {
      const image = document.head.querySelector('meta[property="og:image"]')
      expect(image?.getAttribute('content')).toBe(
        `${SITE_URL}/share/members/${MEMBER_ID}/image`,
      )
    })
  })
})
