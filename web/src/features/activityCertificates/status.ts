/** Presentation labels/chips for activity-certificate status, delivery and awards. */

import type {
  ActivityAwardCategory,
  ActivityCertificateAuditAction,
  ActivityCertificateEmailStatus,
  ActivityCertificateStatus,
} from '../../types/activityCertificate'

export const ACTIVITY_CERTIFICATE_STATUS_LABELS: Record<ActivityCertificateStatus, string> = {
  issued: 'Certificate Issued',
  revoked: 'Revoked',
}

export const ACTIVITY_CERTIFICATE_STATUS_CHIP: Record<ActivityCertificateStatus, string> = {
  issued: 'chip--ok',
  revoked: 'chip--archived',
}

export const ACTIVITY_CERTIFICATE_EMAIL_LABELS: Record<ActivityCertificateEmailStatus, string> = {
  not_sent: 'Not emailed',
  sent: 'Emailed',
  failed: 'Email failed',
}

export const ACTIVITY_CERTIFICATE_EMAIL_CHIP: Record<ActivityCertificateEmailStatus, string> = {
  not_sent: 'chip--muted',
  sent: 'chip--ok',
  failed: 'chip--warn',
}

export const ACTIVITY_AWARD_LABELS: Record<ActivityAwardCategory, string> = {
  first_place: 'First place',
  second_place: 'Second place',
  runner_up: 'Runner-up',
  participation: 'Participation',
  custom: 'Custom award',
}

export const ACTIVITY_CERTIFICATE_AUDIT_LABELS: Record<ActivityCertificateAuditAction, string> = {
  issued: 'Issued',
  revoked: 'Revoked',
  email_sent: 'Email sent',
  email_failed: 'Email failed',
  template_updated: 'Template updated',
}
