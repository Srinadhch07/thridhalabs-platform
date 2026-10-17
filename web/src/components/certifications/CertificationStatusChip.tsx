/** CertificationStatusChip — status pill shared by member and admin views. */

import { CERTIFICATION_STATUS_CHIP, CERTIFICATION_STATUS_LABELS } from '../../features/certifications/status'
import type { CertificationStatus } from '../../types/certification'

export function CertificationStatusChip({ status }: { status: CertificationStatus }) {
  return (
    <span className={`chip ${CERTIFICATION_STATUS_CHIP[status]}`}>
      {CERTIFICATION_STATUS_LABELS[status]}
    </span>
  )
}
