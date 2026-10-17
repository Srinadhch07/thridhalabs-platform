/** Auth feature API module — session bootstrap, login, logout, current account. */

import { api } from '../../lib/api/client'
import { resetCsrfToken } from '../../lib/api/csrf'
import type { StatusResponse } from '../../types/api'
import type { Me } from '../../types/admin'

export function getMe(): Promise<Me> {
  return api.get<Me>('/auth/me')
}

export function login(email: string, password: string): Promise<StatusResponse> {
  // The server rotates the Admin CSRF cookie on login; drop the cached token so
  // the next mutation reads the fresh one instead of a stale value.
  return api
    .post<StatusResponse>('/auth/login', { email, password })
    .finally(() => resetCsrfToken('admin'))
}

export function logout(): Promise<StatusResponse> {
  // Logout deletes the Admin session + CSRF cookies; the cached token is stale.
  return api.post<StatusResponse>('/auth/logout').finally(() => resetCsrfToken('admin'))
}

export function isUnauthenticatedError(error: unknown): boolean {
  return error instanceof Error && (error as { code?: string }).code === 'NOT_AUTHENTICATED'
}