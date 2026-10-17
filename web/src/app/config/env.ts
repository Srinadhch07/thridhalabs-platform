/**
 * Frontend environment contract.
 *
 * Only VITE_* variables are reachable here; they are public by definition and
 * must never carry credentials (Mongo, JWT, AWS, SMTP). The default "/api" is
 * proxied by the Vite dev server to the FastAPI backend.
 */

const rawApiBase: string = (import.meta.env.VITE_API_URL as string | undefined)?.trim() ?? ''

export const env = {
  /** Base URL for the Thridha Labs API (absolute URL or "/api" for the dev proxy). */
  apiBase: rawApiBase ? rawApiBase.replace(/\/+$/, '') : '/api',
  mode: import.meta.env.MODE,
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
} as const

export const API_BASE = env.apiBase