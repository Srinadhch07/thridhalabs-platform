/** Works feature API module — member works (`/member/works`) + public reads. */

import { api } from '../../lib/api/client'
import type { QueryParams } from '../../lib/api/client'
import type { StatusResponse } from '../../types/api'
import type {
  AdminWorkDetail,
  AdminWorkList,
  AdminWorkQuery,
  FeaturedContributionList,
  MemberWork,
  WorkCreatePayload,
  WorkFeaturePayload,
  WorkList,
  WorkPublic,
  WorkQuery,
  WorkReviewDecisionPayload,
  WorkUpdatePayload,
} from '../../types/work'

export function listMemberWorks(query: WorkQuery = {}): Promise<WorkList> {
  return api.get<WorkList>('/member/works', { query: query as QueryParams })
}

export function getMemberWork(workId: string): Promise<MemberWork> {
  return api.get<MemberWork>(`/member/works/${workId}`)
}

export function createMemberWork(payload: WorkCreatePayload): Promise<MemberWork> {
  return api.post<MemberWork>('/member/works', payload)
}

export function updateMemberWork(workId: string, payload: WorkUpdatePayload): Promise<MemberWork> {
  return api.patch<MemberWork>(`/member/works/${workId}`, payload)
}

export function deleteMemberWork(workId: string): Promise<StatusResponse> {
  return api.delete<StatusResponse>(`/member/works/${workId}`)
}

export function publishMemberWork(workId: string): Promise<MemberWork> {
  return api.post<MemberWork>(`/member/works/${workId}/publish`)
}

export function unpublishMemberWork(workId: string): Promise<MemberWork> {
  return api.post<MemberWork>(`/member/works/${workId}/unpublish`)
}

/** Submit a work for publication review (members cannot self-approve). */
export function submitMemberWork(workId: string): Promise<MemberWork> {
  return api.post<MemberWork>(`/member/works/${workId}/submit`)
}

/** Withdraw a pending publication-review submission back to draft. */
export function withdrawMemberWork(workId: string): Promise<MemberWork> {
  return api.post<MemberWork>(`/member/works/${workId}/withdraw`)
}

// --- Admin (publication review + official featuring) ------------------------

export function listAdminWorks(query: AdminWorkQuery = {}): Promise<AdminWorkList> {
  return api.get<AdminWorkList>('/admin/works', { query: query as QueryParams })
}

export function getAdminWork(workId: string): Promise<AdminWorkDetail> {
  return api.get<AdminWorkDetail>(`/admin/works/${workId}`)
}

export function decideAdminWork(
  workId: string,
  payload: WorkReviewDecisionPayload,
): Promise<AdminWorkDetail> {
  return api.post<AdminWorkDetail>(`/admin/works/${workId}/decision`, payload)
}

export function setAdminWorkFeatured(
  workId: string,
  payload: WorkFeaturePayload,
): Promise<AdminWorkDetail> {
  return api.post<AdminWorkDetail>(`/admin/works/${workId}/feature`, payload)
}

// --- Public -----------------------------------------------------------------

export function getPublicWork(memberId: string, slug: string): Promise<WorkPublic> {
  return api.get<WorkPublic>(`/public/members/${memberId}/works/${slug}`)
}

/** Featured member contributions shown on the official Projects page. */
export function getFeaturedContributions(): Promise<FeaturedContributionList> {
  return api.get<FeaturedContributionList>('/public/contributions')
}
