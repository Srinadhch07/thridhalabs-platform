/** Branding feature API module — public and admin endpoints. */

import { api } from '../../lib/api/client'
import type { AdminBranding, PublicBranding } from '../../types/branding'

export function getPublicBranding(): Promise<PublicBranding> {
  return api.get<PublicBranding>('/public/branding')
}

export function getAdminBranding(): Promise<AdminBranding> {
  return api.get<AdminBranding>('/branding')
}

export function updateBranding(payload: unknown): Promise<AdminBranding> {
  return api.put<AdminBranding>('/branding', payload)
}