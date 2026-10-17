/** Branding hooks. */

import { useAsync } from '../../lib/hooks/useAsync'
import { getAdminBranding, getPublicBranding } from './api'

export function usePublicBranding() {
  return useAsync(getPublicBranding, [])
}

export function useAdminBranding() {
  return useAsync(getAdminBranding, [])
}