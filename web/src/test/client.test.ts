/** API client unit tests. */

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api, apiUrl } from '../lib/api/client'
import { ApiError, MalformedResponseError, NetworkError } from '../lib/errors/ApiError'
import { CSRF_HEADER_NAME, getCachedCsrfToken, realmForPath, resetCsrfToken } from '../lib/api/csrf'
import { installFetchMock } from './helpers'

beforeEach(() => {
  resetCsrfToken()
})

describe('apiUrl', () => {
  it('resolves backend paths against the "/api" dev base', () => {
    expect(apiUrl('/public/settings')).toBe('/api/public/settings')
    expect(apiUrl('public/settings')).toBe('/api/public/settings')
  })
})

describe('api.get', () => {
  it('returns parsed JSON and sends cookies plus an accept header', async () => {
    const { calls } = installFetchMock({ '/api/health': { body: { status: 'ok' } } })
    const result = await api.get<{ status: string }>('/health')
    expect(result).toEqual({ status: 'ok' })

    const call = calls.find((c) => c.url.includes('/api/health'))
    expect(call).toBeDefined()
    expect(call?.init?.credentials).toBe('include')
    const headers = call?.init?.headers as Record<string, string>
    expect(headers?.Accept).toBe('application/json')
  })

  it('throws ApiError with code/message for a JSON HTTP error', async () => {
    installFetchMock({
      '/api/things': { status: 404, body: { error: { code: 'NOT_FOUND', message: 'not here' } } },
    })
    try {
      await api.get('/things')
      throw new Error('expected rejection')
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError)
      const apiError = error as ApiError
      expect(apiError.status).toBe(404)
      expect(apiError.code).toBe('NOT_FOUND')
      expect(apiError.message).toBe('not here')
    }
  })

  it('throws ApiError with a generic message for a non-JSON HTTP error', async () => {
    installFetchMock({ '/api/broken': { status: 500, body: 'internal server error', raw: true } })
    try {
      await api.get('/broken')
      throw new Error('expected rejection')
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError)
      expect((error as ApiError).status).toBe(500)
    }
  })

  it('throws MalformedResponseError when a 200 response is not JSON', async () => {
    installFetchMock({ '/api/weird': { body: '<html>oops</html>', raw: true } })
    await expect(api.get('/weird')).rejects.toBeInstanceOf(MalformedResponseError)
  })

  it('throws NetworkError when the request cannot reach the API', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))))
    await expect(api.get('/health')).rejects.toBeInstanceOf(NetworkError)
  })
})

describe('api mutations + CSRF', () => {
  it('bootstraps a CSRF token and sends it as a header on state-changing requests', async () => {
    const { calls } = installFetchMock({
      '/api/auth/csrf': { body: { csrfToken: 'tok-abc' } },
      '/api/things': { status: 201, body: { ok: true } },
    })

    const result = await api.post('/things', { name: 'x' })
    expect(result).toEqual({ ok: true })

    const mutation = calls.find((c) => c.url.includes('/api/things'))
    expect(mutation).toBeDefined()
    expect(mutation?.init?.method).toBe('POST')
    expect(mutation?.init?.credentials).toBe('include')

    const headers = mutation?.init?.headers as Record<string, string>
    expect(headers?.[CSRF_HEADER_NAME]).toBe('tok-abc')
    expect(headers?.['Content-Type']).toBe('application/json')
  })

  it('puts, patches and deletes also send the CSRF header', async () => {
    const { calls } = installFetchMock({
      '/api/auth/csrf': { body: { csrfToken: 'tok-xyz' } },
      '/api/thing': { body: { status: 'ok' } },
    })

    await api.put('/thing', { a: 1 })
    await api.patch('/thing', { a: 2 })
    await api.delete('/thing')

    const mutations = calls.filter((c) => c.url.includes('/api/thing'))
    expect(mutations).toHaveLength(3)
    for (const call of mutations) {
      const headers = call.init?.headers as Record<string, string>
      expect(headers?.[CSRF_HEADER_NAME]).toBe('tok-xyz')
    }
  })

  it('rejects an empty body response (204) returning undefined', async () => {
    const { calls } = installFetchMock({
      '/api/auth/csrf': { body: { csrfToken: 'tok-1' } },
      '/api/thing': { raw: true, status: 204, body: '' },
    })
    const result = await api.delete('/thing')
    expect(result).toBeUndefined()
    expect(calls.filter((c) => c.url.includes('/api/thing'))).toHaveLength(1)
  })
})

describe('per-realm CSRF', () => {
  it('maps member routes to the member realm and everything else to admin', () => {
    expect(realmForPath('/member')).toBe('member')
    expect(realmForPath('/member/works')).toBe('member')
    expect(realmForPath('/members')).toBe('admin')
    expect(realmForPath('/members/123/deactivate')).toBe('admin')
    expect(realmForPath('/auth/me')).toBe('admin')
    expect(realmForPath('/media')).toBe('admin')
  })

  it('bootstraps each realm from its own endpoint and sends the matching token', async () => {
    const { calls } = installFetchMock({
      '/api/auth/csrf': { body: { csrfToken: 'admin-tok' } },
      '/api/member/csrf': { body: { csrfToken: 'member-tok' } },
      '/api/things': { status: 201, body: { ok: true } },
      '/api/member/works': { status: 201, body: { ok: true } },
    })

    await api.post('/things', { name: 'x' })
    await api.post('/member/works', { title: 'y' })

    const adminCall = calls.find((c) => c.url.includes('/api/things'))
    const memberCall = calls.find((c) => c.url.includes('/api/member/works'))
    const adminHeaders = adminCall?.init?.headers as Record<string, string>
    const memberHeaders = memberCall?.init?.headers as Record<string, string>

    expect(adminHeaders?.[CSRF_HEADER_NAME]).toBe('admin-tok')
    expect(memberHeaders?.[CSRF_HEADER_NAME]).toBe('member-tok')
    expect(getCachedCsrfToken('admin')).toBe('admin-tok')
    expect(getCachedCsrfToken('member')).toBe('member-tok')
  })

  it('caches tokens per realm (one bootstrap each)', async () => {
    const { calls } = installFetchMock({
      '/api/auth/csrf': { body: { csrfToken: 'admin-tok' } },
      '/api/member/csrf': { body: { csrfToken: 'member-tok' } },
      '/api/things': { status: 201, body: {} },
      '/api/member/works': { status: 201, body: {} },
    })

    await api.post('/things')
    await api.post('/things')
    await api.post('/member/works')
    await api.post('/member/works')

    expect(calls.filter((c) => c.url.includes('/api/auth/csrf'))).toHaveLength(1)
    expect(calls.filter((c) => c.url.includes('/api/member/csrf'))).toHaveLength(1)
  })

  it('a CSRF_INVALID response resets only that realm\'s cached token', async () => {
    const { calls } = installFetchMock({
      '/api/auth/csrf': { body: { csrfToken: 'admin-tok' } },
      '/api/member/csrf': { body: { csrfToken: 'member-tok' } },
      '/api/things': {
        status: 403,
        body: { error: { code: 'CSRF_INVALID', message: 'bad' } },
      },
      '/api/member/works': { status: 201, body: {} },
    })

    await api.post('/things').catch(() => undefined)
    await api.post('/member/works')
    await api.post('/things').catch(() => undefined)

    expect(calls.filter((c) => c.url.includes('/api/auth/csrf'))).toHaveLength(2)
    expect(calls.filter((c) => c.url.includes('/api/member/csrf'))).toHaveLength(1)
  })

  it('resetCsrfToken(realm) clears a single realm; no-arg clears all', async () => {
    const { calls } = installFetchMock({
      '/api/auth/csrf': { body: { csrfToken: 'admin-tok' } },
      '/api/member/csrf': { body: { csrfToken: 'member-tok' } },
      '/api/things': { status: 201, body: {} },
      '/api/member/works': { status: 201, body: {} },
    })

    await api.post('/member/works')
    await api.post('/things')
    resetCsrfToken('member')

    expect(getCachedCsrfToken('member')).toBeNull()
    expect(getCachedCsrfToken('admin')).toBe('admin-tok')

    await api.post('/member/works')
    await api.post('/things')

    expect(calls.filter((c) => c.url.includes('/api/member/csrf'))).toHaveLength(2)
    expect(calls.filter((c) => c.url.includes('/api/auth/csrf'))).toHaveLength(1)

    resetCsrfToken()
    expect(getCachedCsrfToken('admin')).toBeNull()
    expect(getCachedCsrfToken('member')).toBeNull()
  })
})