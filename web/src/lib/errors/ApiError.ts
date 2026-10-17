/**
 * API client error hierarchy.
 *
 * - ApiError: the API responded with a non-2xx status (parsed error payload).
 * - NetworkError: the request never reached the API (no response).
 * - MalformedResponseError: a response arrived but was not valid JSON.
 *
 * Error messages shown to users must never include stack traces or raw
 * internals; `getErrorMessage` returns only safe, user-presentable text.
 */

export interface ApiErrorFields {
  [field: string]: string
}

export class ApiError extends Error {
  readonly status: number
  readonly code?: string
  readonly fields?: ApiErrorFields

  constructor(
    status: number,
    code?: string,
    message?: string,
    fields?: ApiErrorFields,
  ) {
    super(message ?? `Request failed with status ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.fields = fields
  }
}

export class NetworkError extends Error {
  constructor(message = 'Unable to reach the API. Please check your connection and try again.') {
    super(message)
    this.name = 'NetworkError'
  }
}

export class MalformedResponseError extends Error {
  constructor(message = 'The API returned an unexpected response.') {
    super(message)
    this.name = 'MalformedResponseError'
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}

export function isNetworkError(error: unknown): error is NetworkError {
  return error instanceof NetworkError
}

export function getErrorMessage(error: unknown, fallback = 'Please try again later.'): string {
  if (typeof error === 'string') {
    return error
  }
  if (error instanceof ApiError || error instanceof NetworkError || error instanceof MalformedResponseError) {
    return error.message
  }
  return fallback
}