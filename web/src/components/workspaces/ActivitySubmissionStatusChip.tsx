/** Colored status chip for an activity submission. */

import { ACTIVITY_SUBMISSION_STATUS_LABELS } from '../../types/activitySubmission'
import type { ActivitySubmissionStatus } from '../../types/activitySubmission'

const STATUS_CHIP: Record<ActivitySubmissionStatus, string> = {
  pending: 'chip--admin',
  changes_requested: 'chip--warn',
  approved: 'chip--ok',
  rejected: 'chip--danger',
}

export function ActivitySubmissionStatusChip({
  status,
}: {
  status: ActivitySubmissionStatus
}) {
  return (
    <span className={`chip ${STATUS_CHIP[status]}`}>
      {ACTIVITY_SUBMISSION_STATUS_LABELS[status]}
    </span>
  )
}
