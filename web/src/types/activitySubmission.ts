/**
 * Activity workspace types (`/member/activity-workspaces` +
 * `/member/activity-submissions` + `/admin/activity-submissions`).
 *
 * Participation is **individual**: one student owns their own progress updates
 * and at most one deliverable per programme/hackathon. There is no team
 * concept anywhere in this surface.
 *
 * Lifecycle: `pending → approved` or `pending → changes_requested → (student
 * edits/resubmits) → pending`, plus `rejected` as the final rejection. Every
 * admin decision is appended to `review_history` (never overwritten).
 */

import type { ActivityPresentationStatus } from './activity'

export type ActivitySubmissionKind = 'progress_update' | 'deliverable'
export type ActivitySubmissionStatus =
  | 'pending'
  | 'changes_requested'
  | 'approved'
  | 'rejected'
export type ActivitySubmissionDecisionAction = 'approve' | 'request_changes' | 'reject'

export const MAX_SUBMISSION_TITLE_LENGTH = 150
export const MAX_SUBMISSION_DESCRIPTION_LENGTH = 5000
export const MAX_SUBMISSION_URL_LENGTH = 2000
export const MAX_SUBMISSION_EVIDENCE_LINKS = 10
export const MAX_SUBMISSION_ATTACHMENTS = 10

/** Deliverable parts an activity may require. */
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

export const ACTIVITY_SUBMISSION_STATUS_LABELS: Record<ActivitySubmissionStatus, string> = {
  pending: 'Awaiting review',
  changes_requested: 'Changes requested',
  approved: 'Approved',
  rejected: 'Rejected',
}

/** One immutable admin decision, appended to a submission's review history. */
export interface ActivitySubmissionReviewEntry {
  status: ActivitySubmissionStatus
  reviewer_name: string | null
  feedback: string | null
  version: number
  decided_at: string
}

/** A snapshot of the content the student submitted in an earlier version. */
export interface ActivitySubmissionRevision {
  version: number
  title: string | null
  description: string
  repository_url: string | null
  demo_url: string | null
  evidence_links: string[]
  submitted_at: string
}

/** Member-facing view of one of the member's own submissions. */
export interface ActivitySubmission {
  id: string
  activity_id: string
  activity_slug: string
  activity_title: string
  activity_type: string
  member_id: string
  member_readable_id: string
  kind: ActivitySubmissionKind
  title: string | null
  description: string
  repository_url: string | null
  demo_url: string | null
  evidence_links: string[]
  attachment_media_ids: string[]
  status: ActivitySubmissionStatus
  version: number
  editable: boolean
  submitted_at: string
  updated_at: string
  reviewed_at: string | null
  reviewed_by: string | null
  review_feedback: string | null
  review_history: ActivitySubmissionReviewEntry[]
  revisions: ActivitySubmissionRevision[]
}

/** Admin view of any submission (review queue + detail). */
export interface AdminActivitySubmission extends ActivitySubmission {
  member_name: string | null
  member_email: string | null
}

/** One activity task plus the member's own completion state. */
export interface ActivityTask {
  id: string
  title: string
  description: string
  due_date: string | null
  completed: boolean
}

export interface ActivityResource {
  label: string
  url: string
}

/** Everything one member needs for one activity workspace. */
export interface ActivityWorkspace {
  activity_id: string
  slug: string
  title: string
  activity_type: string
  summary: string
  description: string
  presentation_status: ActivityPresentationStatus
  start_date: string | null
  end_date: string | null
  banner_media_id: string | null
  has_brief: boolean
  objectives: string[]
  instructions: string
  requirements: string[]
  resources: ActivityResource[]
  required_deliverables: RequiredDeliverable[]
  participation_status: string | null
  participation_role: string | null
  tasks: ActivityTask[]
  completed_task_count: number
  task_count: number
  progress_percent: number
  deliverable: ActivitySubmission | null
  progress_updates: ActivitySubmission[]
  can_submit: boolean
  submit_blocked_reason: string | null
}

export interface ActivityWorkspaceList {
  items: ActivityWorkspace[]
}

/** Admin view of one student's individual record inside one activity. */
export interface AdminStudentActivity {
  activity_id: string
  activity_slug: string
  activity_title: string
  activity_type: string
  member_id: string
  member_readable_id: string
  member_name: string | null
  member_email: string | null
  participation_status: string
  participation_role: string | null
  participation_source: string
  confirmed_at: string | null
  tasks: ActivityTask[]
  completed_task_count: number
  task_count: number
  progress_percent: number
  submissions: AdminActivitySubmission[]
}

// --- Payloads + queries -----------------------------------------------------

export interface ActivitySubmissionCreatePayload {
  activity_id: string
  kind: ActivitySubmissionKind
  title?: string | null
  description: string
  repository_url?: string | null
  demo_url?: string | null
  evidence_links?: string[]
  attachment_media_ids?: string[]
  /** Optional idempotency key so a retried submit cannot create duplicates. */
  client_request_id?: string | null
}

export interface ActivitySubmissionUpdatePayload {
  title?: string | null
  description: string
  repository_url?: string | null
  demo_url?: string | null
  evidence_links?: string[]
  attachment_media_ids?: string[]
}

export interface ActivitySubmissionDecisionPayload {
  action: ActivitySubmissionDecisionAction
  feedback?: string | null
}

export interface ActivityTaskCompletionPayload {
  task_id: string
  completed: boolean
}

export interface ActivitySubmissionListQuery {
  page?: number
  page_size?: number
}

export interface AdminActivitySubmissionQuery {
  page?: number
  page_size?: number
  status?: ActivitySubmissionStatus
  kind?: ActivitySubmissionKind
  activity_id?: string
  member_id?: string
}
