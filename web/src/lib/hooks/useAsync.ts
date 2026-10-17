/**
 * Lightweight async-data hook used across the feature hooks.
 *
 * Local state only — no query library for Phase 5. `reload()` re-runs the
 * async function; callers control cache/reset via the returned state.
 */

import { useCallback, useEffect, useState } from 'react'

export interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: Error | null
  reload: () => void
}

export function useAsync<T>(asyncFn: () => Promise<T>, deps: ReadonlyArray<unknown> = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [tick, setTick] = useState(0)

  const reload = useCallback(() => {
    setTick((value) => value + 1)
  }, [])

  useEffect(() => {
    let cancelled = false

    async function run(): Promise<void> {
      setLoading(true)
      setError(null)
      try {
        const result = await asyncFn()
        if (!cancelled) {
          setData(result)
          setLoading(false)
        }
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof Error ? caught : new Error(String(caught)))
          setLoading(false)
        }
      }
    }

    void run()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])

  return { data, loading, error, reload }
}