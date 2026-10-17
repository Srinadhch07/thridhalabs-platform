/** Shared API envelope types mirroring the backend contracts. */

export interface ErrorResponse {
  error: {
    code: string
    message: string
    fields?: Record<string, string>
  }
}

export interface StatusResponse {
  status: 'ok'
}

export interface Health {
  status: string
  app: string
  version: string
  environment: string
  timestamp: string
}

export interface Ready {
  status: 'ready' | 'degraded'
  checks: { mongo: 'up' | 'down'; latency_ms: number | null }
  timestamp: string
}

export interface CsrfResponse {
  csrfToken: string
}