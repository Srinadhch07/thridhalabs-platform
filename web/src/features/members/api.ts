/** Members feature API module — member self-service (`/member`) + admin CRUD (`/members`). */

import { api, upload } from '../../lib/api/client'
import { resetCsrfToken } from '../../lib/api/csrf'
import type { QueryParams } from '../../lib/api/client'
import type { StatusResponse } from '../../types/api'
import type { Media } from '../../types/media'
import type {
  MemberAdmin,
  MemberCreatePayload,
  MemberListQuery,
  MemberMe,
  MemberProfilePayload,
  MemberProfileResponse,
  MemberSetupPayload,
  MemberUpdatePayload,
  PublicMemberProfile,
} from '../../types/member'
import type { Paginated } from '../../types/pagination'

// --- Member self-service ---------------------------------------------------

export function getMemberMe(): Promise<MemberMe> {
  return api.get<MemberMe>('/member/me')
}

export function memberSetup(payload: MemberSetupPayload): Promise<StatusResponse> {
  return api.post<StatusResponse>('/member/setup', payload)
}

export function memberLogin(email: string, password: string): Promise<StatusResponse> {
  // The server rotates the Member CSRF cookie on login; discard the cached one.
  return api
    .post<StatusResponse>('/member/login', { email, password })
    .finally(() => resetCsrfToken('member'))
}

export function memberLogout(): Promise<StatusResponse> {
  // Logout deletes the Member session + CSRF cookies; the cached token is stale.
  return api.post<StatusResponse>('/member/logout').finally(() => resetCsrfToken('member'))
}

export function getMemberProfile(): Promise<MemberProfileResponse> {
  return api.get<MemberProfileResponse>('/member/profile')
}

export function updateMemberProfile(payload: MemberProfilePayload): Promise<MemberProfileResponse> {
  return api.patch<MemberProfileResponse>('/member/profile', payload)
}

export function changeMemberPassword(
  currentPassword: string,
  newPassword: string,
): Promise<StatusResponse> {
  return api.post<StatusResponse>('/member/password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}

export function uploadMemberPicture(file: File): Promise<Media> {
  return upload<Media>('/member/picture', file)
}

export function clearMemberPicture(): Promise<MemberProfileResponse> {
  return api.delete<MemberProfileResponse>('/member/picture')
}

// --- Admin -----------------------------------------------------------------

export function listMembers(query: MemberListQuery = {}): Promise<Paginated<MemberAdmin>> {
  return api.get<Paginated<MemberAdmin>>('/members', { query: query as QueryParams })
}

export function getMember(memberId: string): Promise<MemberAdmin> {
  return api.get<MemberAdmin>(`/members/${memberId}`)
}

export function createMember(payload: MemberCreatePayload): Promise<MemberAdmin> {
  return api.post<MemberAdmin>('/members', payload)
}

export function updateMember(memberId: string, payload: MemberUpdatePayload): Promise<MemberAdmin> {
  return api.patch<MemberAdmin>(`/members/${memberId}`, payload)
}

export function resendMemberOnboarding(memberId: string): Promise<MemberAdmin> {
  return api.post<MemberAdmin>(`/members/${memberId}/resend`)
}

export function deactivateMember(memberId: string): Promise<MemberAdmin> {
  return api.post<MemberAdmin>(`/members/${memberId}/deactivate`)
}

export function reactivateMember(memberId: string): Promise<MemberAdmin> {
  return api.post<MemberAdmin>(`/members/${memberId}/reactivate`)
}

export function deleteMember(memberId: string): Promise<StatusResponse> {
  return api.delete<StatusResponse>(`/members/${memberId}`)
}

// --- Public -----------------------------------------------------------------

export function getPublicMember(memberId: string): Promise<PublicMemberProfile> {
  return api.get<PublicMemberProfile>(`/public/members/${memberId}`)
}