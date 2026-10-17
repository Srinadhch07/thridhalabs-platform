/** Settings feature API module — public and admin endpoints. */

import { api } from '../../lib/api/client'
import type { AdminSiteSettings, PublicSiteSettings } from '../../types/settings'

export function getPublicSettings(): Promise<PublicSiteSettings> {
  return api.get<PublicSiteSettings>('/public/settings')
}

export function getAdminSettings(): Promise<AdminSiteSettings> {
  return api.get<AdminSiteSettings>('/settings')
}

export function updateSettings(payload: unknown): Promise<AdminSiteSettings> {
  return api.put<AdminSiteSettings>('/settings', payload)
}