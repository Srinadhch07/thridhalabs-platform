/** Presentation labels + chips for progress-report status and decisions. */

import type { ReportDecisionAction, ReportStatus } from '../../types/report'

export const REPORT_STATUS_LABELS: Record<ReportStatus, string> = {
  pending: 'Awaiting review',
  changes_requested: 'Changes requested',
  approved: 'Approved',
}

export const REPORT_STATUS_CHIP: Record<ReportStatus, string> = {
  pending: 'chip--admin',
  changes_requested: 'chip--warn',
  approved: 'chip--ok',
}

export const REPORT_DECISION_LABELS: Record<ReportDecisionAction, string> = {
  approve: 'Approve',
  request_changes: 'Request changes',
}

/** Decisions that require reviewer feedback. */
export const REPORT_DECISION_FEEDBACK_ACTIONS: ReportDecisionAction[] = ['request_changes']
