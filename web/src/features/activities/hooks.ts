/** Activities hooks. */

import { useAsync } from '../../lib/hooks/useAsync'
import type { ActivityAdminQuery, PublicActivityQuery } from '../../types/activity'
import {
  getAdminActivity,
  getPublicActivity,
  listAdminActivities,
  listActivityParticipants,
  listMemberActivities,
  listPublicActivities,
} from './api'

export function useAdminActivities(query: ActivityAdminQuery = {}) {
  return useAsync(() => listAdminActivities(query), [JSON.stringify(query)])
}

export function useAdminActivity(activityId: string | undefined) {
  return useAsync(
    async () => {
      if (!activityId) throw new Error('Missing activity id')
      return getAdminActivity(activityId)
    },
    [activityId],
  )
}

export function useActivityParticipants(
  activityId: string | undefined,
  query: { page?: number; page_size?: number; status?: string } = {},
) {
  return useAsync(
    async () => {
      if (!activityId) throw new Error('Missing activity id')
      return listActivityParticipants(activityId, query)
    },
    [activityId, JSON.stringify(query)],
  )
}

export function usePublicActivities(query: PublicActivityQuery = {}) {
  return useAsync(() => listPublicActivities(query), [JSON.stringify(query)])
}

export function usePublicActivity(slug: string | undefined) {
  return useAsync(
    async () => {
      if (!slug) throw new Error('Missing activity slug')
      return getPublicActivity(slug)
    },
    [slug],
  )
}

export function useMemberActivities() {
  return useAsync(() => listMemberActivities(), [])
}
