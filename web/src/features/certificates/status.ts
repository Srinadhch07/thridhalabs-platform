/** Presentation labels/chips for certificate status and email delivery. */

import type { CertificateEmailStatus, CertificateStatus } from '../../types/certificate'

export const CERTIFICATE_STATUS_LABELS: Record<CertificateStatus, string> = {
  issued: 'Certificate Issued',
  revoked: 'Revoked',
}

export const CERTIFICATE_STATUS_CHIP: Record<CertificateStatus, string> = {
  issued: 'chip--ok',
  revoked: 'chip--archived',
}

export const CERTIFICATE_EMAIL_LABELS: Record<CertificateEmailStatus, string> = {
  not_sent: 'Not emailed',
  sent: 'Emailed',
  failed: 'Email failed',
}

export const CERTIFICATE_EMAIL_CHIP: Record<CertificateEmailStatus, string> = {
  not_sent: 'chip--muted',
  sent: 'chip--ok',
  failed: 'chip--warn',
}
