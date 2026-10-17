/**
 * Centralized API client.
 *
 * - base URL resolution (VITE_API_URL or the "/api" dev proxy)
 * - JSON request/response handling
 * - credentials-included cookies for the HttpOnly session
 * - automatic CSRF header on state-changing requests
 * - typed responses via generics
 * - consistent error classes (ApiError / NetworkError / MalformedResponseError)
 *
 * React components must go through `api.*` helpers, never raw `fetch()`.
 */

import { API_BASE } from '../../app/config/env'
import { ApiError, MalformedResponseError, NetworkError } from '../errors/ApiError'
import { CSRF_HEADER_NAME, ensureCsrfToken, realmForPath, resetCsrfToken } from './csrf'
import type { AuthRealm } from './csrf'

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export type QueryParams = Record<string, string | number | boolean | null | undefined>

export interface RequestOptions {
  query?: QueryParams
  body?: unknown
  headers?: Record<string, string>
  /** Force a CSRF realm; defaults to the realm inferred from the path. */
  realm?: AuthRealm
  signal?: AbortSignal
}

const MUTATING_METHODS: ReadonlySet<HttpMethod> = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

/** Resolve a backend path (e.g. "/public/settings") against the API base. */
export function apiUrl(path: string): string {
  const clean = path.startsWith('/') ? path : `/${path}`
  if (API_BASE === '/' || clean.startsWith(API_BASE)) return clean
  return `${API_BASE}${clean}`
}

function buildUrl(path: string, query: QueryParams | undefined): string {
  const url = apiUrl(path)
  if (!query) return url
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) continue
    params.set(key, String(value))
  }
  const qs = params.toString()
  return qs ? `${url}?${qs}` : url
}

interface ErrorBody {
  error?: { code?: string; message?: string; fields?: Record<string, string> }
}

function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === 'AbortError'
}

async function parseErrorBody(res: Response): Promise<ErrorBody | null> {
  try {
    const body = (await res.json()) as ErrorBody
    return body && typeof body === 'object' ? body : null
  } catch {
    return null
  }
}

export async function request<T>(path: string, options: RequestOptions & { method: HttpMethod }): Promise<T> {
  const { method, query, body, headers, signal } = options
  const realm = options.realm ?? realmForPath(path)
  const requestHeaders: Record<string, string> = { Accept: 'application/json', ...headers }

  let requestBody: BodyInit | undefined
  if (body !== undefined) {
    requestHeaders['Content-Type'] = 'application/json'
    requestBody = JSON.stringify(body)
  }

  if (MUTATING_METHODS.has(method)) {
    requestHeaders[CSRF_HEADER_NAME] = await ensureCsrfToken(realm)
  }

  let res: Response
  try {
    res = await fetch(buildUrl(path, query), {
      method,
      headers: requestHeaders,
      body: requestBody,
      credentials: 'include',
      signal,
    })
  } catch (error) {
    if (isAbortError(error)) throw error
    throw new NetworkError()
  }

  if (!res.ok) {
    const errorBody = await parseErrorBody(res)
    const code = errorBody?.error?.code
    if (res.status === 403 && code === 'CSRF_INVALID') {
      resetCsrfToken(realm)
    }
    throw new ApiError(
      res.status,
      typeof code === 'string' ? code : undefined,
      errorBody?.error?.message,
      errorBody?.error?.fields,
    )
  }

  if (res.status === 204) return undefined as T

  const text = await res.text()
  if (!text) return undefined as T
  try {
    return JSON.parse(text) as T
  } catch {
    throw new MalformedResponseError()
  }
}

export async function upload<T>(
  path: string,
  file: File,
  options: Omit<RequestOptions, 'body' | 'headers'> = {},
): Promise<T> {
  const realm = options.realm ?? realmForPath(path)
  const body = new FormData()
  body.append('file', file)
  const requestHeaders: Record<string, string> = { Accept: 'application/json' }
  requestHeaders[CSRF_HEADER_NAME] = await ensureCsrfToken(realm)

  let res: Response
  try {
    res = await fetch(buildUrl(path, options.query), {
      method: 'POST',
      headers: requestHeaders,
      body,
      credentials: 'include',
      signal: options.signal,
    })
  } catch (error) {
    if (isAbortError(error)) throw error
    throw new NetworkError()
  }

  if (!res.ok) {
    const errorBody = await parseErrorBody(res)
    const code = errorBody?.error?.code
    if (res.status === 403 && code === 'CSRF_INVALID') {
      resetCsrfToken(realm)
    }
    throw new ApiError(
      res.status,
      typeof code === 'string' ? code : undefined,
      errorBody?.error?.message,
      errorBody?.error?.fields,
    )
  }

  if (res.status === 204) return undefined as T
  const text = await res.text()
  if (!text) return undefined as T
  try {
    return JSON.parse(text) as T
  } catch {
    throw new MalformedResponseError()
  }
}

export const api = {
  get<T>(path: string, options: Omit<RequestOptions, 'body'> = {}): Promise<T> {
    return request<T>(path, { ...options, method: 'GET' })
  },
  post<T>(path: string, body?: unknown, options: Omit<RequestOptions, 'body'> = {}): Promise<T> {
    return request<T>(path, { ...options, method: 'POST', body })
  },
  put<T>(path: string, body?: unknown, options: Omit<RequestOptions, 'body'> = {}): Promise<T> {
    return request<T>(path, { ...options, method: 'PUT', body })
  },
  patch<T>(path: string, body?: unknown, options: Omit<RequestOptions, 'body'> = {}): Promise<T> {
    return request<T>(path, { ...options, method: 'PATCH', body })
  },
  delete<T>(path: string, options: Omit<RequestOptions, 'body'> = {}): Promise<T> {
    return request<T>(path, { ...options, method: 'DELETE' })
  },
}

export interface DownloadedFile {
  blob: Blob
  filename: string | null
}

function filenameFromDisposition(header: string | null): string | null {
  if (!header) return null
  const match = /filename\*?=(?:UTF-8''|")?([^";]+)/i.exec(header)
  if (!match) return null
  try {
    return decodeURIComponent(match[1].trim().replace(/^"|"$/g, ''))
  } catch {
    return match[1].trim().replace(/^"|"$/g, '')
  }
}

/** Fetch a binary file (PDF) with session cookies; never sends CSRF (safe GET). */
export async function downloadFile(
  path: string,
  options: { query?: QueryParams; signal?: AbortSignal } = {},
): Promise<DownloadedFile> {
  let res: Response
  try {
    res = await fetch(buildUrl(path, options.query), {
      method: 'GET',
      headers: { Accept: 'application/pdf, application/octet-stream' },
      credentials: 'include',
      signal: options.signal,
    })
  } catch (error) {
    if (isAbortError(error)) throw error
    throw new NetworkError()
  }

  if (!res.ok) {
    const errorBody = await parseErrorBody(res)
    throw new ApiError(
      res.status,
      errorBody?.error?.code,
      errorBody?.error?.message,
      errorBody?.error?.fields,
    )
  }

  return {
    blob: await res.blob(),
    filename: filenameFromDisposition(res.headers.get('content-disposition')),
  }
}