/**
 * CSRF client support (double-submit scheme).
 *
 * The backend stores each realm's JWT in a dedicated HttpOnly cookie and its
 * CSRF token in a dedicated *readable* cookie:
 *
 *   - Admin:  GET /auth/csrf   → thridha_labs_csrf
 *   - Member: GET /member/csrf → thridha_labs_member_csrf
 *
 * Every state-changing request must echo the realm's cookie value in the
 * `X-CSRF-Token` header. This module is the single place that obtains/reads the
 * token and keeps one cache per realm, so an Admin and a Member session never
 * share or invalidate each other's token.
 */

import { API_BASE } from '../../app/config/env'
import { ApiError } from '../errors/ApiError'

export const CSRF_HEADER_NAME = 'X-CSRF-Token'

/** Which authentication realm an API request belongs to. */
export type AuthRealm = 'admin' | 'member'

interface RealmCsrfConfig {
  cookieName: string
  bootstrapPath: string
}

/** Kept in sync with the backend cookie defaults (`app/core/config.py`). */
const REALMS: Record<AuthRealm, RealmCsrfConfig> = {
  admin: { cookieName: 'thridha_labs_csrf', bootstrapPath: '/auth/csrf' },
  member: { cookieName: 'thridha_labs_member_csrf', bootstrapPath: '/member/csrf' },
}

const cachedTokens: Record<AuthRealm, string | null> = { admin: null, member: null }

/**
 * Resolve the realm for a backend path. Member endpoints are all mounted under
 * `/member` (e.g. `/member/works`); the admin member-management API is
 * `/members`, so the trailing slash/segment boundary matters.
 */
export function realmForPath(path: string): AuthRealm {
  return path === '/member' || path.startsWith('/member/') ? 'member' : 'admin'
}

function cookieNameFor(realm: AuthRealm): string {
  return REALMS[realm].cookieName
}

function readCsrfCookie(realm: AuthRealm): string | null {
  if (typeof document === 'undefined') return null
  const prefix = `${cookieNameFor(realm)}=`
  for (const part of document.cookie.split(';')) {
    const entry = part.trim()
    if (entry.startsWith(prefix)) {
      return decodeURIComponent(entry.slice(prefix.length)) || null
    }
  }
  return null
}

export function getCachedCsrfToken(realm: AuthRealm = 'admin'): string | null {
  return cachedTokens[realm]
}

/**
 * Bootstrap a realm's CSRF token when needed: reuse the in-memory token, fall
 * back to that realm's readable cookie, then hit its bootstrap endpoint (which
 * also re-sets the cookie).
 */
export async function ensureCsrfToken(realm: AuthRealm = 'admin'): Promise<string> {
  if (cachedTokens[realm]) return cachedTokens[realm]

  const fromCookie = readCsrfCookie(realm)
  if (fromCookie) {
    cachedTokens[realm] = fromCookie
    return fromCookie
  }

  const res = await fetch(`${API_BASE}${REALMS[realm].bootstrapPath}`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })

  if (!res.ok) {
    throw new ApiError(res.status, 'CSRF_NOT_AVAILABLE', 'Unable to obtain a CSRF token')
  }

  const token = (await res.json().catch(() => null))?.csrfToken
  cachedTokens[realm] = typeof token === 'string' && token ? token : readCsrfCookie(realm)
  if (!cachedTokens[realm]) {
    throw new ApiError(500, 'CSRF_NOT_AVAILABLE', 'Unable to obtain a CSRF token')
  }
  return cachedTokens[realm]
}

/**
 * Drop a cached token so it is re-fetched. Pass a realm to invalidate just that
 * realm; omit it to clear every realm.
 */
export function resetCsrfToken(realm?: AuthRealm): void {
  if (realm) {
    cachedTokens[realm] = null
    return
  }
  cachedTokens.admin = null
  cachedTokens.member = null
}
