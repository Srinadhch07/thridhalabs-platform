/** Activity workspaces feature API — member workspace + admin review queue. */

import { api } from '../../lib/api/client'
import type { QueryParams } from '../../lib/api/client'
import type { Paginated } from '../../types/pagination'
import type {
  ActivitySubmission,
  ActivitySubmissionCreatePayload,
  ActivitySubmissionDecisionPayload,
  ActivitySubmissionListQuery,
  ActivitySubmissionUpdatePayload,
  ActivityTaskCompletionPayload,
  ActivityWorkspace,
  ActivityWorkspaceList,
  AdminActivitySubmission,
  AdminActivitySubmissionQuery,
  AdminStudentActivity,
} from '../../types/activitySubmission'

// --- Member -----------------------------------------------------------------

export function listMyActivityWorkspaces(): Promise<ActivityWorkspaceList> {
  return api.get<ActivityWorkspaceList>('/member/activity-workspaces')
}

export function getMyActivityWorkspace(slug: string): Promise<ActivityWorkspace> {
  return api.get<ActivityWorkspace>(`/member/activity-workspaces/${slug}`)
}

export function setActivityTaskCompletion(
  slug: string,
  payload: ActivityTaskCompletionPayload,
): Promise<ActivityWorkspace> {
  return api.patch<ActivityWorkspace>(`/member/activity-workspaces/${slug}/tasks`, payload)
}

export function listMyActivitySubmissions(
  query: ActivitySubmissionListQuery = {},
): Promise<Paginated<ActivitySubmission>> {
  return api.get<Paginated<ActivitySubmission>>('/member/activity-submissions', {
    query: query as QueryParams,
  })
}

export function createActivitySubmission(
  payload: ActivitySubmissionCreatePayload,
): Promise<ActivitySubmission> {
  return api.post<ActivitySubmission>('/member/activity-submissions', payload)
}

export function updateActivitySubmission(
  submissionId: string,
  payload: ActivitySubmissionUpdatePayload,
): Promise<ActivitySubmission> {
  return api.patch<ActivitySubmission>(`/member/activity-submissions/${submissionId}`, payload)
}

// --- Admin ------------------------------------------------------------------

export function listAdminActivitySubmissions(
  query: AdminActivitySubmissionQuery = {},
): Promise<Paginated<AdminActivitySubmission>> {
  return api.get<Paginated<AdminActivitySubmission>>('/admin/activity-submissions', {
    query: query as QueryParams,
  })
}

export function listAdminActivitySubmissionsForActivity(
  activityId: string,
  query: { page?: number; page_size?: number; status?: string; kind?: string } = {},
): Promise<Paginated<AdminActivitySubmission>> {
  return api.get<Paginated<AdminActivitySubmission>>(
    `/admin/activity-submissions/activity/${activityId}`,
    { query: query as QueryParams },
  )
}

export function getAdminStudentActivity(
  activityId: string,
  memberId: string,
): Promise<AdminStudentActivity> {
  return api.get<AdminStudentActivity>(
    `/admin/activity-submissions/activity/${activityId}/students/${memberId}`,
  )
}

export function decideAdminActivitySubmission(
  submissionId: string,
  payload: ActivitySubmissionDecisionPayload,
): Promise<AdminActivitySubmission> {
  return api.post<AdminActivitySubmission>(
    `/admin/activity-submissions/${submissionId}/decision`,
    payload,
  )
}
