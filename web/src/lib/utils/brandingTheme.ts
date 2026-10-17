/**
 * Runtime theme layer driven by the branding API.
 *
 * Branding colors are exposed as CSS variables on the document root. The
 * fallback palette (tokens.css) is the safe default used whenever the API is
 * unavailable, so the application never renders blank because branding failed.
 */

import type { PublicBranding } from '../../types/branding'

export const BRANDING_CSS_VARS = {
  primary: '--color-primary',
  secondary: '--color-secondary',
  accent: '--color-accent',
  background: '--color-background',
  text: '--color-text',
} as const

export function applyBranding(branding: PublicBranding): { root: HTMLElement } | null {
  if (typeof document === 'undefined') return null
  const root = document.documentElement
  root.style.setProperty(BRANDING_CSS_VARS.primary, branding.colors.primary)
  root.style.setProperty(BRANDING_CSS_VARS.secondary, branding.colors.secondary)
  root.style.setProperty(BRANDING_CSS_VARS.accent, branding.colors.accent)
  root.style.setProperty(BRANDING_CSS_VARS.background, branding.colors.background)
  root.style.setProperty(BRANDING_CSS_VARS.text, branding.colors.text)
  root.style.colorScheme = branding.mode
  return { root }
}