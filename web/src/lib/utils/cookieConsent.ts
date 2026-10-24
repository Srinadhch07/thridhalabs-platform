/**
 * Cookie consent storage and helpers
 */

const COOKIE_CONSENT_KEY = 'thridha_cookie_consent_v1'

export type ConsentCategory = 'necessary' | 'analytics' | 'marketing'

export interface CookieConsent {
  version: 1
  necessary: true
  analytics: boolean
  marketing: boolean
  timestamp: number
}

export function getCookieConsent(): CookieConsent | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(COOKIE_CONSENT_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as CookieConsent
    if (parsed?.version !== 1) return null
    return { ...parsed, necessary: true }
  } catch {
    return null
  }
}

export function setCookieConsent(consent: Omit<CookieConsent, 'version' | 'necessary' | 'timestamp'>): CookieConsent {
  const value: CookieConsent = {
    version: 1,
    necessary: true,
    analytics: !!consent.analytics,
    marketing: !!consent.marketing,
    timestamp: Date.now(),
  }
  if (typeof window !== 'undefined') {
    try {
      window.localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify(value))
    } catch {
      // ignore
    }
  }
  return value
}

export function hasAnalyticsConsent(): boolean {
  return !!getCookieConsent()?.analytics
}

export function hasMarketingConsent(): boolean {
  return !!getCookieConsent()?.marketing
}
