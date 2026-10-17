/** Presentation labels/chips for certification status and review actions. */

import type { CertificationReviewAction, CertificationStatus } from '../../types/certification'

export const CERTIFICATION_STATUS_LABELS: Record<CertificationStatus, string> = {
  submitted: 'Submitted',
  under_review: 'Request Under Review',
  changes_requested: 'Changes Requested',
  approved: 'Approved',
  rejected: 'Rejected',
}

export const CERTIFICATION_STATUS_CHIP: Record<CertificationStatus, string> = {
  submitted: 'chip--muted',
  under_review: 'chip--admin',
  changes_requested: 'chip--warn',
  approved: 'chip--ok',
  rejected: 'chip--archived',
}

export const CERTIFICATION_ACTION_LABELS: Record<CertificationReviewAction, string> = {
  under_review: 'Mark under review',
  approve: 'Approve',
  request_changes: 'Request changes',
  reject: 'Reject',
}

/** Feedback is mandatory for these reviewer actions (mirrors the backend). */
export const CERTIFICATION_FEEDBACK_ACTIONS: CertificationReviewAction[] = [
  'request_changes',
  'reject',
]
