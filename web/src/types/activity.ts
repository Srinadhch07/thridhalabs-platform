/**
 * Activity types (`/admin/activities`, `/member/activities`, `/public/activities`).
 *
 * Activities unify three offerings under one lifecycle: **Project**
 * (invitation-only), **Programme** and **Hackathon** (open self-registration).
 * Only `published` activities are ever listed publicly; a `cancelled` activity
 * stays reachable by slug but is clearly marked and never promoted. The
 * presentation label (`status_label`) is derived from the stored lifecycle plus
 * the dates — the stored status is the source of truth.
 */

export type ActivityType = 'project' | 'programme' | 'hackathon'
export type ActivityStatus = 'draft' | 'published' | 'cancelled' | 'archived'
export type ActivityPresentationStatus =
  | 'upcoming'
  | 'ongoing'
  | 'completed'
  | 'cancelled'
  | 'archived'
export type ParticipationStatus =
  | 'invited'
  | 'interested'
  | 'declined'
  | 'confirmed'
  | 'withdrawn'
export type ParticipationSource = 'invited' | 'self_registered'

export interface BriefRef {
  version: number
  filename: string
  size_bytes: number
  uploaded_at: string
}

/** A link shown to participants in the workspace. */
export interface ActivityResource {
  label: string
  url: string
}

/** One personal checklist task inside an activity. */
export interface ActivityTask {
  id: string
  title: string
  description: string
  due_date: string | null
}

/** Parts of the deliverable an activity expects participants to provide. */
export type RequiredDeliverable =
  | 'description'
  | 'repository_url'
  | 'demo_url'
  | 'evidence_links'

export const REQUIRED_DELIVERABLE_LABELS: Record<RequiredDeliverable, string> = {
  description: 'Description',
  repository_url: 'Repository URL',
  demo_url: 'Demo URL',
  evidence_links: 'Evidence links',
}

export const REQUIRED_DELIVERABLE_OPTIONS: RequiredDeliverable[] = [
  'description',
  'repository_url',
  'demo_url',
  'evidence_links',
]

/** Full admin view of an activity. */
export interface AdminActivity {
  id: string
  title: string
  slug: string
  activity_type: ActivityType
  summary: string
  description: string
  status: ActivityStatus
  presentation_status: ActivityPresentationStatus
  start_date: string | null
  end_date: string | null
  banner_media_id: string | null
  featured: boolean
  display_order: number
  roles_offered: string[]
  tags: string[]
  objectives: string[]
  instructions: string
  requirements: string[]
  resources: ActivityResource[]
  tasks: ActivityTask[]
  required_deliverables: RequiredDeliverable[]
  brief: BriefRef | null
  brief_history_count: number
  cancel_reason: string | null
  participant_counts: Record<string, number>
  created_at: string
  updated_at: string
  published_at: string | null
  cancelled_at: string | null
  archived_at: string | null
}

export interface AdminActivityList {
  items: AdminActivity[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface ActivityCreatePayload {
  title: string
  slug?: string | null
  activity_type: ActivityType
  summary?: string
  description?: string
  status?: ActivityStatus
  start_date?: string | null
  end_date?: string | null
  banner_media_id?: string | null
  featured?: boolean
  display_order?: number
  roles_offered?: string[]
  tags?: string[]
  objectives?: string[]
  instructions?: string
  requirements?: string[]
  resources?: ActivityResource[]
  tasks?: ActivityTask[]
  required_deliverables?: RequiredDeliverable[]
  cancel_reason?: string | null
}

export type ActivityUpdatePayload = Partial<ActivityCreatePayload>

export interface ActivityAdminQuery {
  page?: number
  page_size?: number
  sort?: 'display_order' | 'created_at' | 'start_date' | 'end_date' | 'title'
  order?: 'asc' | 'desc'
  status?: ActivityStatus
  activity_type?: ActivityType
  featured?: boolean
}

export interface ActivityParticipant {
  id: string
  activity_id: string
  member_id: string
  member_readable_id: string
  member_name: string | null
  member_email: string | null
  role: string | null
  status: ParticipationStatus
  source: ParticipationSource
  note: string | null
  invited_at: string | null
  responded_at: string | null
  confirmed_at: string | null
  withdrawn_at: string | null
  email_sent_at: string | null
  created_at: string
  updated_at: string
}

export interface ActivityParticipantList {
  items: ActivityParticipant[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface InvitationItem {
  member_id: string
  role?: string | null
}

export interface InvitationRequest {
  invitations: InvitationItem[]
  subject?: string | null
  message?: string | null
}

export interface InvitationResult {
  invited: number
  re_invited: number
  emails_sent: number
  email_failures: number
  skipped: string[]
  errors: string[]
}

export interface ParticipantUpdatePayload {
  status?: ParticipationStatus | null
  role?: string | null
  note?: string | null
}

// --- Public surfaces --------------------------------------------------------

export interface PublicActivity {
  slug: string
  title: string
  activity_type: ActivityType
  summary: string
  description: string
  presentation_status: ActivityPresentationStatus
  start_date: string | null
  end_date: string | null
  banner_media_id: string | null
  featured: boolean
  display_order: number
  roles_offered: string[]
  tags: string[]
  has_brief: boolean
  registration_open: boolean
}

export interface PublicActivityList {
  items: PublicActivity[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface PublicActivityQuery {
  page?: number
  page_size?: number
  activity_type?: ActivityType
  featured?: boolean
  sort?: 'display_order' | 'start_date' | 'end_date' | 'title'
  order?: 'asc' | 'desc'
}

// --- Member surfaces --------------------------------------------------------

export interface MemberActivity {
  slug: string
  title: string
  activity_type: ActivityType
  summary: string
  presentation_status: ActivityPresentationStatus
  start_date: string | null
  end_date: string | null
  banner_media_id: string | null
  has_brief: boolean
  registration_open: boolean
  can_register: boolean
  can_withdraw: boolean
  participation_status: ParticipationStatus | null
  participation_role: string | null
}

export interface MemberActivityList {
  items: MemberActivity[]
}
