/**
 * Project Progress Report types (`/member/reports` + `/admin/reports`).
 *
 * A progress report is a short, member-authored update about work on a
 * *project* activity. Only a **confirmed participant** of a project may submit
 * a report for it, and only `approved` reports feed the member's contribution
 * history — which stays a private member-portal surface, never published to the
 * public portfolio.
 *
 * Lifecycle: `pending → approved` or `pending → changes_requested → (author
 * edits/resubmits) → pending`. Every admin decision is appended to
 * `review_history` (never overwritten), so the full review trail survives a
 * resubmission.
 */

import type { ActivityPresentationStatus } from './activity'
import type { ContributionSummary } from './ai'

export type ReportStatus = 'pending' | 'changes_requested' | 'approved'
export type ReportDecisionAction = 'approve' | 'request_changes'
export type ReportSort = 'submitted_at' | 'updated_at' | 'reviewed_at'

export const MAX_REPORT_DESCRIPTION_LENGTH = 500
export const MAX_REPORT_EVIDENCE_LINKS = 10

/** One immutable admin decision, appended to a report's review history. */
export interface ReportReviewEntry {
  status: ReportStatus
  reviewer_name: string | null
  feedback: string | null
  /** Content version that was reviewed (detects edits since review). */
  version: number
  decided_at: string
}

/** Member-facing view of one of the member's own reports. */
export interface MemberReport {
  id: string
  activity_id: string
  activity_slug: string
  activity_title: string
  role: string | null
  description: string
  evidence_links: string[]
  status: ReportStatus
  version: number
  editable: boolean
  submitted_at: string
  updated_at: string
  reviewed_at: string | null
  review_feedback: string | null
  review_history: ReportReviewEntry[]
}

/** A project the member is a confirmed participant of, with report roll-ups. */
export interface MemberProjectSummary {
  activity_id: string
  slug: string
  title: string
  role: string | null
  presentation_status: ActivityPresentationStatus
  start_date: string | null
  end_date: string | null
  banner_media_id: string | null
  report_count: number
  pending_count: number
  changes_requested_count: number
  approved_count: number
  last_report_at: string | null
}

export interface MemberProjectList {
  items: MemberProjectSummary[]
}

/** One approved report as it appears in the contribution history. */
export interface ContributionReport {
  id: string
  description: string
  evidence_links: string[]
  approved_at: string
  submitted_at: string
}

export interface ContributionProjectGroup {
  activity_id: string
  slug: string
  title: string
  role: string | null
  report_count: number
  reports: ContributionReport[]
  /** Explicitly published, Admin-reviewed AI summaries for this project. */
  summaries: ContributionSummary[]
}

export interface ContributionHistory {
  items: ContributionProjectGroup[]
  total_reports: number
}

/** Admin view of any report (review queue + detail). */
export interface AdminReport {
  id: string
  activity_id: string
  activity_slug: string
  activity_title: string
  member_id: string
  member_readable_id: string
  member_name: string
  member_email: string | null
  role: string | null
  description: string
  evidence_links: string[]
  status: ReportStatus
  version: number
  submitted_at: string
  updated_at: string
  reviewed_at: string | null
  reviewed_by: string | null
  review_feedback: string | null
  review_history: ReportReviewEntry[]
}

// --- Payloads + queries -----------------------------------------------------

export interface ReportCreatePayload {
  activity_id: string
  description: string
  evidence_links?: string[]
  /** Optional idempotency key so a retried submit cannot create duplicates. */
  client_request_id?: string | null
}

export interface ReportUpdatePayload {
  description: string
  evidence_links?: string[]
}

export interface ReportDecisionPayload {
  action: ReportDecisionAction
  feedback?: string | null
}

export interface ReportListQuery {
  page?: number
  page_size?: number
  activity_id?: string
}

export interface AdminReportQuery {
  page?: number
  page_size?: number
  status?: ReportStatus
  activity_id?: string
  member_id?: string
  search?: string
  sort?: ReportSort
  order?: 'asc' | 'desc'
}
