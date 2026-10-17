/** CertificateStatusChip — issued/revoked pill shared by member/admin/public views. */

import { CERTIFICATE_STATUS_CHIP, CERTIFICATE_STATUS_LABELS } from '../../features/certificates/status'
import type { CertificateStatus } from '../../types/certificate'

export function CertificateStatusChip({ status }: { status: CertificateStatus }) {
  return (
    <span className={`chip ${CERTIFICATE_STATUS_CHIP[status]}`}>
      {CERTIFICATE_STATUS_LABELS[status]}
    </span>
  )
}
