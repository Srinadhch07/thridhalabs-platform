/** Activities feature API — admin CRUD/participants + public + member reads. */

import { api, downloadFile, upload } from '../../lib/api/client'
import type { DownloadedFile, QueryParams } from '../../lib/api/client'
import type { StatusResponse } from '../../types/api'
import type {
  ActivityAdminQuery,
  ActivityCreatePayload,
  ActivityParticipantList,
  ActivityParticipant,
  ActivityUpdatePayload,
  AdminActivity,
  AdminActivityList,
  InvitationRequest,
  InvitationResult,
  MemberActivity,
  MemberActivityList,
  ParticipantUpdatePayload,
  PublicActivity,
  PublicActivityList,
  PublicActivityQuery,
} from '../../types/activity'

// --- Admin ------------------------------------------------------------------
export function listAdminActivities(query: ActivityAdminQuery = {}): Promise<AdminActivityList> {
  return api.get<AdminActivityList>('/admin/activities', { query: query as QueryParams })
}

export function getAdminActivity(activityId: string): Promise<AdminActivity> {
  return api.get<AdminActivity>(`/admin/activities/${activityId}`)
}

export function createAdminActivity(payload: ActivityCreatePayload): Promise<AdminActivity> {
  return api.post<AdminActivity>('/admin/activities', payload)
}

export function updateAdminActivity(
  activityId: string,
  payload: ActivityUpdatePayload,
): Promise<AdminActivity> {
  return api.patch<AdminActivity>(`/admin/activities/${activityId}`, payload)
}

export function deleteAdminActivity(activityId: string): Promise<StatusResponse> {
  return api.delete<StatusResponse>(`/admin/activities/${activityId}`)
}

export function uploadActivityBrief(activityId: string, file: File): Promise<AdminActivity> {
  return upload<AdminActivity>(`/admin/activities/${activityId}/brief`, file)
}

export function removeActivityBrief(activityId: string): Promise<AdminActivity> {
  return api.delete<AdminActivity>(`/admin/activities/${activityId}/brief`)
}

export function downloadAdminActivityBrief(activityId: string): Promise<DownloadedFile> {
  return downloadFile(`/admin/activities/${activityId}/brief`)
}

export function inviteToActivity(
  activityId: string,
  payload: InvitationRequest,
): Promise<InvitationResult> {
  return api.post<InvitationResult>(`/admin/activities/${activityId}/invitations`, payload)
}

export function listActivityParticipants(
  activityId: string,
  query: { page?: number; page_size?: number; status?: string } = {},
): Promise<ActivityParticipantList> {
  return api.get<ActivityParticipantList>(`/admin/activities/${activityId}/participants`, {
    query: query as QueryParams,
  })
}

export function updateActivityParticipant(
  activityId: string,
  participationId: string,
  payload: ParticipantUpdatePayload,
): Promise<ActivityParticipant> {
  return api.patch<ActivityParticipant>(
    `/admin/activities/${activityId}/participants/${participationId}`,
    payload,
  )
}

// --- Public -----------------------------------------------------------------
export function listPublicActivities(query: PublicActivityQuery = {}): Promise<PublicActivityList> {
  return api.get<PublicActivityList>('/public/activities', { query: query as QueryParams })
}

export function getPublicActivity(slug: string): Promise<PublicActivity> {
  return api.get<PublicActivity>(`/public/activities/${slug}`)
}

export function downloadPublicActivityBrief(slug: string): Promise<DownloadedFile> {
  return downloadFile(`/public/activities/${slug}/brief`)
}

// --- Member -----------------------------------------------------------------
export function listMemberActivities(): Promise<MemberActivityList> {
  return api.get<MemberActivityList>('/member/activities')
}

export function registerForActivity(slug: string): Promise<MemberActivity> {
  return api.post<MemberActivity>(`/member/activities/${slug}/register`)
}

export function withdrawFromActivity(slug: string): Promise<MemberActivity> {
  return api.post<MemberActivity>(`/member/activities/${slug}/withdraw`)
}
