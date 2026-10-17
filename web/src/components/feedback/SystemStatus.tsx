/**
 * System status — foundation connectivity probe.
 *
 * Proves the frontend can reach the API through the shared client and the
 * Vite proxy: GET /api/health and GET /api/health/ready.
 */

import { useEffect, useState } from 'react'
import { api } from '../../lib/api/client'
import type { Health, Ready } from '../../types'

type Phase = 'checking' | 'ok' | 'degraded' | 'error'

export default function SystemStatus() {
  const [phase, setPhase] = useState<Phase>('checking')
  const [health, setHealth] = useState<Health | null>(null)
  const [ready, setReady] = useState<Ready | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function probe(): Promise<void> {
      try {
        const healthResult = await api.get<Health>('/health', { signal: controller.signal })
        setHealth(healthResult)
        try {
          const readyResult = await api.get<Ready>('/health/ready', { signal: controller.signal })
          setReady(readyResult)
          setPhase(readyResult.status === 'ready' ? 'ok' : 'degraded')
        } catch {
          setPhase('degraded')
        }
      } catch (error) {
        if (!(error instanceof Error && error.name === 'AbortError')) {
          setPhase('error')
        }
      }
    }

    void probe()
    return () => controller.abort()
  }, [])

  const dotClass =
    phase === 'ok'
      ? 'status-dot status-dot--ok'
      : phase === 'checking'
        ? 'status-dot status-dot--pending'
        : 'status-dot status-dot--err'

  const label =
    phase === 'checking'
      ? 'checking systems…'
      : phase === 'ok'
        ? 'all systems nominal'
        : phase === 'degraded'
          ? 'api up · database unreachable'
          : 'api unreachable'

  return (
    <div className="card mono" style={{ fontSize: 'var(--fs-sm)' }}>
      <p className="tag" style={{ marginBottom: 'var(--space-3)' }}>
        System status
      </p>
      <p style={{ margin: 0, color: 'var(--ink-dim)' }}>
        <span className={dotClass} aria-hidden="true" />
        {label}
      </p>
      {health && (
        <p style={{ margin: 'var(--space-2) 0 0', color: 'var(--faint)' }}>
          {health.app} v{health.version} · {health.environment}
        </p>
      )}
      {ready && (
        <p style={{ margin: 'var(--space-1) 0 0', color: 'var(--faint)' }}>
          mongo: {ready.checks.mongo}
          {ready.checks.latency_ms != null ? ` · ${ready.checks.latency_ms}ms` : ''}
        </p>
      )}
    </div>
  )
}