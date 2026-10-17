/** Media hooks. */

import { useAsync } from '../../lib/hooks/useAsync'
import { listMedia, listMemberMedia } from './api'
import type { MediaQuery } from '../../types/media'

export function useMediaList(query: MediaQuery = {}) {
  return useAsync(() => listMedia(query), [JSON.stringify(query)])
}

export function useMemberMediaList(query: MediaQuery = {}) {
  return useAsync(() => listMemberMedia(query), [JSON.stringify(query)])
}