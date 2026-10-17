/**
 * SiteSettingsProvider — global site settings consumed via `useSiteSettings()`.
 *
 * Avoids fetching the same settings separately in every page. The public
 * settings payload includes `maintenance_mode`, which the public layout uses
 * to route to the maintenance page; admin access is intentionally unaffected
 * so the owner can disable maintenance mode.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { getPublicSettings } from '../../features/settings/api'
import type { PublicSiteSettings } from '../../types/settings'

export type SettingsStatus = 'loading' | 'success' | 'error'

interface SettingsContextValue {
  status: SettingsStatus
  data: PublicSiteSettings | null
  error: Error | null
  maintenanceEnabled: boolean
  reload: () => Promise<void>
}

const SettingsContext = createContext<SettingsContextValue | null>(null)

export function SiteSettingsProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<SettingsStatus>('loading')
  const [data, setData] = useState<PublicSiteSettings | null>(null)
  const [error, setError] = useState<Error | null>(null)

  const reload = useCallback(async () => {
    setStatus('loading')
    setError(null)
    try {
      const settings = await getPublicSettings()
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
      maintenanceEnabled: data?.maintenance_mode === true,
      reload,
    }),
    [status, data, error, reload],
  )

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>
}

export function useSiteSettings(): SettingsContextValue {
  const context = useContext(SettingsContext)
  if (!context) {
    throw new Error('useSiteSettings must be used within a <SiteSettingsProvider>')
  }
  return context
}