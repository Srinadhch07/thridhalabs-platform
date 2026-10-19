/**
 * Frontend environment contract.
 *
 * Only VITE_* variables are reachable here; they are public by definition and
 * must never carry credentials (Mongo, JWT, AWS, SMTP). The default "/api" is
 * proxied by the Vite dev server to the FastAPI backend.
 */

const rawApiBase: string = (import.meta.env.VITE_API_URL as string | undefined)?.trim() ?? ''
const rawSiteUrl: string = (import.meta.env.VITE_SITE_URL as string | undefined)?.trim() ?? ''

/** Strip a trailing slash so origin joins stay clean. */
function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '')
}

/** A configured, absolute http(s) production origin (e.g. https://thridhalabs.com). */
export const SITE_URL: string = rawSiteUrl ? trimTrailingSlash(rawSiteUrl) : ''

export const env = {
  /** Base URL for the Thridha Labs API (absolute URL or "/api" for the dev proxy). */
  apiBase: rawApiBase ? trimTrailingSlash(rawApiBase) : '/api',
  /**
   * Canonical production origin for SEO (canonical URLs, OG/Twitter, sitemap).
   * Empty until the domain is configured via VITE_SITE_URL; SEO URL helpers then
   * refuse to emit production-dependent tags rather than publish localhost.
   */
  siteUrl: SITE_URL,
  mode: import.meta.env.MODE,
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
} as const

export const API_BASE = env.apiBase