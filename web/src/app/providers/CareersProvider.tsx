/**
 * CareersProvider — global careers settings consumed via `useCareers()`.
 *
 * The public payload includes a public `enabled` flag (plain system state,
 * same rationale as `maintenance_mode`). Navigation and the footer use it to
 * render the Careers link only when the singleton is enabled; the public page
 * uses it to fall back to the 404 treatment otherwise.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { getPublicCareersSettings } from '../../features/careers/api'
import type { PublicCareersSettings } from '../../types/careers'

export type CareersStatus = 'loading' | 'success' | 'error'

interface CareersContextValue {
  status: CareersStatus
  data: PublicCareersSettings | null
  error: Error | null
  enabled: boolean
  reload: () => Promise<void>
}

const CareersContext = createContext<CareersContextValue | null>(null)

export function CareersProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<CareersStatus>('loading')
  const [data, setData] = useState<PublicCareersSettings | null>(null)
  const [error, setError] = useState<Error | null>(null)

  const reload = useCallback(async () => {
    setStatus('loading')
    setError(null)
    try {
      const settings = await getPublicCareersSettings()
      setData(settings)
      setStatus('success')
    } catch (caught) {
      setError(caught instanceof Error ? caught : new Error(String(caught)))
      setStatus('error')
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  const value = useMemo(
    () => ({
      status,
      data,
      error,
      enabled: data?.enabled === true,
      reload,
    }),
    [status, data, error, reload],
  )

  return <CareersContext.Provider value={value}>{children}</CareersContext.Provider>
}

export function useCareers(): CareersContextValue {
  const context = useContext(CareersContext)
  if (!context) {
    throw new Error('useCareers must be used within a <CareersProvider>')
  }
  return context
}