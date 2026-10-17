/** Certification-review types (`/member/certifications` + `/admin/certifications`).
 *
 * Each request freezes an immutable snapshot of a published work at submission
 * time; the reviewer only ever judges that snapshot. `changed_since_review` is
 * derived from the frozen snapshot version vs the live work version and is
 * never silently cleared.
 */

import type { ContentDocument, ExternalLink } from './work'
import type { CertificateRef } from './certificate'

export type CertificationStatus =
  | 'submitted'
  | 'under_review'
  | 'changes_requested'
  | 'approved'
  | 'rejected'

export type CertificationReviewAction = 'under_review' | 'approve' | 'request_changes' | 'reject'

export interface CertificationSnapshot {
  slug: string
  title: string
  summary: string
  cover_media_id: string | null
  tags: string[]
  external_links: ExternalLink[]
  content: ContentDocument
}

export interface CertificationDecision {
  action: string
  by: string
  by_role: string
  at: string
  feedback: string | null
}

export interface CertificationWorkRef {
  id: string
  title: string
  slug: string
}

export interface CertificationMemberRef {
  member_id: string
  name: string
}

/** List item — excludes the heavy snapshot. */
export interface CertificationCard {
  id: string
  status: CertificationStatus
  active: boolean
  work: CertificationWorkRef
  member: CertificationMemberRef
  snapshot_version: number
  version_reviewed: number
  changed_since_review: boolean
  submitted_at: string
  decided_at: string | null
}

export interface CertificationDetail {
  id: string
  status: CertificationStatus
  active: boolean
  work: CertificationWorkRef
  member: CertificationMemberRef
  snapshot: CertificationSnapshot
  snapshot_version: number
  version_reviewed: number
  changed_since_review: boolean
  captured_at: string
  submitted_at: string
  decided_at: string | null
  decided_by: string | null
  decided_by_role: string | null
  latest_feedback: string | null
  decisions: CertificationDecision[]
  created_at: string
  updated_at: string
  certificate: CertificateRef | null
}

export interface CertificationList {
  items: CertificationCard[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface CertificationApplyPayload {
  work_id: string
}

export interface CertificationDecisionPayload {
  action: CertificationReviewAction
  feedback?: string | null
}

export interface CertificationQuery {
  page?: number
  page_size?: number
  status?: CertificationStatus
}
