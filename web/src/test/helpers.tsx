/** Test helpers — fetch mocking and app-level render utilities. */

import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { ReactElement } from 'react'
import { vi } from 'vitest'
import App from '../App'
import { brandingFixture, careersSettingsFixture, emptyList, settingsFixture } from './fixtures'

export interface FetchCall {
  url: string
  init?: RequestInit
}

export interface MockHandler {
  status?: number
  body?: unknown
  headers?: HeadersInit
  /** When true, respond with raw text instead of JSON (status still 200). */
  raw?: boolean
}

export type HandlerMap = Record<
  string,
  MockHandler | ((url: string, init?: RequestInit) => MockHandler)
>

export function jsonResponse(status: number, body: unknown, headers?: HeadersInit): Response {
  return new Response(JSON.stringify(body ?? null), {
    status,
    headers: { 'Content-Type': 'application/json', ...(headers ?? {}) },
  })
}

/**
 * Replace the global fetch with a stub driven by pathname -> handler.
 * Returns the recorded calls for assertions.
 */
export function installFetchMock(handlers: HandlerMap): { calls: FetchCall[] } {
  const calls: FetchCall[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : String(input)
    calls.push({ url, init })
    const path = url.replace(/^https?:\/\/[^/]+/, '').split('?')[0]
    const handler = handlers[path] ?? handlers[url]
    if (!handler) {
      return jsonResponse(404, { error: { code: 'NOT_FOUND', message: 'not stubbed' } })
    }
    const resolved = typeof handler === 'function' ? handler(url, init) : handler
    const status = resolved.status ?? 200
    if (resolved.raw) {
      // 204/304 must not carry a body (undici rejects a body on no-content statuses).
      const body = status === 204 ? null : String(resolved.body ?? '')
      return new Response(body, { status })
    }
    return jsonResponse(status, resolved.body ?? null, resolved.headers)
  })
  vi.stubGlobal('fetch', fetchMock)
  return { calls }
}

export function defaultHandlers(): HandlerMap {
  return {
    '/api/auth/me': {
      status: 401,
      body: { error: { code: 'NOT_AUTHENTICATED', message: 'Authentication required' } },
    },
    '/api/member/me': {
      status: 401,
      body: { error: { code: 'NOT_AUTHENTICATED', message: 'Authentication required' } },
    },
    '/api/public/settings': { body: settingsFixture },
    '/api/public/branding': { body: brandingFixture },
    '/api/public/careers/settings': { body: careersSettingsFixture },
    '/api/public/projects': { body: emptyList() },
    '/api/public/activities': { body: emptyList() },
    '/api/public/contributions': { body: { items: [] } },
    '/api/public/clients': { body: emptyList() },
    '/api/public/testimonials': { body: emptyList() },
  }
}

export interface RenderAppOptions {
  entry?: string
  handlers?: HandlerMap
}

export function renderApp(options: RenderAppOptions = {}): { calls: FetchCall[] } {
  const { entry = '/', handlers = {} } = options
  const { calls } = installFetchMock({ ...defaultHandlers(), ...handlers })
  const ui: ReactElement = (
    <MemoryRouter initialEntries={[entry]}>
      <App />
    </MemoryRouter>
  )
  render(ui)
  return { calls }
}