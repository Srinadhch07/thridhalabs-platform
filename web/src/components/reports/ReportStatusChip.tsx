/** Colored status chip for a progress report. */

import { REPORT_STATUS_CHIP, REPORT_STATUS_LABELS } from '../../features/reports/labels'
import type { ReportStatus } from '../../types/report'

export function ReportStatusChip({ status }: { status: ReportStatus }) {
  return (
    <span className={`chip ${REPORT_STATUS_CHIP[status]}`}>{REPORT_STATUS_LABELS[status]}</span>
  )
}
