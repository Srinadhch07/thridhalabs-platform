/** Settings hooks. */

import { useAsync } from '../../lib/hooks/useAsync'
import { getAdminSettings, getPublicSettings } from './api'

export function usePublicSettings() {
  return useAsync(getPublicSettings, [])
}

export function useAdminSettings() {
  return useAsync(getAdminSettings, [])
}