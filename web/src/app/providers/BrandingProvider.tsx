/**
 * BrandingProvider — applies branding API values as CSS variables at runtime.
 *
 * On failure the fallback palette (tokens.css) remains active, so the app is
 * always usable even if the branding API is down.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { getPublicBranding } from '../../features/branding/api'
import { applyBranding } from '../../lib/utils/brandingTheme'
import { resolveMediaUrl } from '../../lib/utils/mediaUrl'
import type { PublicBranding } from '../../types/branding'

export type BrandingStatus = 'loading' | 'success' | 'error'

interface BrandingContextValue {
  status: BrandingStatus
  data: PublicBranding | null
  error: Error | null
  reload: () => Promise<void>
}

const BrandingContext = createContext<BrandingContextValue | null>(null)

export function BrandingProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<BrandingStatus>('loading')
  const [data, setData] = useState<PublicBranding | null>(null)
  const [error, setError] = useState<Error | null>(null)

  const reload = useCallback(async () => {
    setStatus('loading')
    setError(null)
    try {
      const branding = await getPublicBranding()
      setData(branding)
      setStatus('success')
      applyBranding(branding)
    } catch (caught) {
      setError(caught instanceof Error ? caught : new Error(String(caught)))
      setStatus('error')
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  const value = useMemo(
    () => ({ status, data, error, reload }),
    [status, data, error, reload],
  )

  // Favicon is part of the brand (runtime-driven); the link tag is created on
  // first use and reused on rebrand, so an image URL is always applied. The
  // backend guarantees public media resolution for a known media id.
  useEffect(() => {
    if (!data?.media.favicon) return
    const href = resolveMediaUrl(data.media.favicon, 'thumb')
    if (!href) return
    let link = document.querySelector<HTMLLinkElement>("link[rel~='icon']")
    if (!link) {
      link = document.createElement('link')
      link.rel = 'icon'
      document.head.appendChild(link)
    }
    link.href = href
  }, [data])

  return <BrandingContext.Provider value={value}>{children}</BrandingContext.Provider>
}

export function useBranding(): BrandingContextValue {
  const context = useContext(BrandingContext)
  if (!context) {
    throw new Error('useBranding must be used within a <BrandingProvider>')
  }
  return context
}