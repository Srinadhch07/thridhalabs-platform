/** Activity workspaces hooks. */

import { useAsync } from '../../lib/hooks/useAsync'
import type {
  AdminActivitySubmissionQuery,
  ActivitySubmissionListQuery,
} from '../../types/activitySubmission'
import {
  getAdminStudentActivity,
  getMyActivityWorkspace,
  listAdminActivitySubmissions,
  listAdminActivitySubmissionsForActivity,
  listMyActivityWorkspaces,
} from './api'

export function useMyActivityWorkspaces() {
  return useAsync(() => listMyActivityWorkspaces(), [])
}

export function useMyActivityWorkspace(slug: string | undefined) {
  return useAsync(
    async () => {
      if (!slug) throw new Error('Missing activity slug')
      return getMyActivityWorkspace(slug)
    },
    [slug],
  )
}

export function useAdminActivitySubmissions(query: AdminActivitySubmissionQuery = {}) {
  return useAsync(() => listAdminActivitySubmissions(query), [JSON.stringify(query)])
}

export function useAdminActivitySubmissionsForActivity(
  activityId: string | undefined,
  query: { page?: number; page_size?: number; status?: string; kind?: string } = {},
) {
  return useAsync(
    async () => {
      if (!activityId) throw new Error('Missing activity id')
      return listAdminActivitySubmissionsForActivity(activityId, query)
    },
    [activityId, JSON.stringify(query)],
  )
}

export function useAdminStudentActivity(
  activityId: string | undefined,
  memberId: string | undefined,
) {
  return useAsync(
    async () => {
      if (!activityId || !memberId) throw new Error('Missing activity or member id')
      return getAdminStudentActivity(activityId, memberId)
    },
    [activityId, memberId],
  )
}

export type { ActivitySubmissionListQuery }
