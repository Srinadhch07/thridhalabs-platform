/** Lab Member Account types (Phase 9 `/member` + `/members` APIs). */

import type { WorkPublicCard } from './work'

export type MemberStatus = 'pending_setup' | 'active' | 'inactive'

/** Controls how much of a member's showcase is publicly visible. */
export type ProfileVisibility = 'private' | 'members' | 'public'

export interface MemberProfileInfo {
  display_name: string | null
  bio: string | null
  skills: string[]
  interests: string[]
  github_url: string | null
  linkedin_url: string | null
  portfolio_url: string | null
  location: string | null
  timezone: string | null
  picture_media_id: string | null
  profile_visibility: ProfileVisibility
  completed_at: string | null
}

/** `/member/me` — the member's own session identity. */
export interface MemberMe {
  id: string
  member_id: string
  email: string
  status: MemberStatus
  full_name: string | null
  profile_complete: boolean
  last_login_at: string | null
}

/** `/member/profile` — the member's own editable profile. */
export interface MemberProfileResponse {
  id: string
  member_id: string
  email: string
  status: MemberStatus
  full_name: string | null
  role_label: string | null
  profile: MemberProfileInfo
  profile_complete: boolean
  created_at: string
}

/** `/members` — admin view of a member account. */
export interface MemberAdmin {
  id: string
  member_id: string
  email: string
  status: MemberStatus
  full_name: string | null
  role_label: string | null
  joined_opportunity_id: string | null
  internal_note: string | null
  profile: MemberProfileInfo
  profile_complete: boolean
  onboarding_sent: boolean
  onboarding_completed_at: string | null
  created_by: string
  created_at: string
  updated_at: string
  last_login_at: string | null
}

export interface MemberCreatePayload {
  email: string
  full_name?: string | null
  role_label?: string | null
  joined_opportunity_id?: string | null
  internal_note?: string | null
}

export interface MemberUpdatePayload {
  email?: string
  full_name?: string | null
  role_label?: string | null
  joined_opportunity_id?: string | null
  internal_note?: string | null
}

export interface MemberProfilePayload {
  display_name?: string | null
  bio?: string | null
  skills?: string[]
  interests?: string[]
  github_url?: string | null
  linkedin_url?: string | null
  portfolio_url?: string | null
  location?: string | null
  timezone?: string | null
  profile_visibility?: ProfileVisibility
}

export interface MemberSetupPayload {
  token: string
  password: string
}

export interface MemberListQuery {
  page?: number
  page_size?: number
  sort?: string
  order?: 'asc' | 'desc'
  status?: MemberStatus | ''
  search?: string
}

/** A published, Admin-reviewed AI contribution summary on a public profile. */
export interface PublicContributionSummary {
  activity_title: string
  role: string | null
  content: string
  published_at: string
  source_report_count: number
  period_start: string | null
  period_end: string | null
}

/** `/public/members/{member_id}` — a public member profile and their works. */
export interface PublicMemberProfile {
  member_id: string
  display_name: string
  bio: string | null
  skills: string[]
  interests: string[]
  github_url: string | null
  linkedin_url: string | null
  portfolio_url: string | null
  location: string | null
  picture_media_id: string | null
  works: WorkPublicCard[]
  contributions: PublicContributionSummary[]
}