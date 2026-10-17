/** Works hooks. */

import { useAsync } from '../../lib/hooks/useAsync'
import type { AdminWorkQuery, WorkQuery } from '../../types/work'
import {
  getAdminWork,
  getFeaturedContributions,
  getMemberWork,
  getPublicWork,
  listAdminWorks,
  listMemberWorks,
} from './api'

export function useMemberWorks(query: WorkQuery = {}) {
  return useAsync(() => listMemberWorks(query), [JSON.stringify(query)])
}

export function useMemberWork(workId: string | undefined) {
  return useAsync(
    async () => {
      if (!workId) throw new Error('Missing work id')
      return getMemberWork(workId)
    },
    [workId],
  )
}

export function usePublicWork(memberId: string | undefined, slug: string | undefined) {
  return useAsync(
    async () => {
      if (!memberId || !slug) throw new Error('Missing member id or slug')
      return getPublicWork(memberId, slug)
    },
    [memberId, slug],
  )
}

export function useAdminWorks(query: AdminWorkQuery = {}) {
  return useAsync(() => listAdminWorks(query), [JSON.stringify(query)])
}

export function useAdminWork(workId: string | undefined) {
  return useAsync(
    async () => {
      if (!workId) throw new Error('Missing work id')
      return getAdminWork(workId)
    },
    [workId],
  )
}

export function useFeaturedContributions() {
  return useAsync(() => getFeaturedContributions(), [])
}
