/** Activity certificate types — participation/award credentials for activities.
 *
 * Distinct from the Work Recognition Certificate: an Activity Certificate
 * recognises a person's participation or award in a programme/hackathon/project.
 * The public verification projection never includes member email, storage keys,
 * member internal ids or reviewer identity.
 */

export type ActivityCertificateStatus = 'issued' | 'revoked'
export type ActivityCertificateEmailStatus = 'not_sent' | 'sent' | 'failed'
export type ActivityAwardCategory =
  | 'first_place'
  | 'second_place'
  | 'runner_up'
  | 'participation'
  | 'custom'
export type ActivityCertificateAuditAction =
  | 'issued'
  | 'revoked'
  | 'email_sent'
  | 'email_failed'
  | 'template_updated'

export interface ActivityCertificateMember {
  certificate_id: string
  activity_title: string
  activity_slug: string
  activity_type: string
  award_category: ActivityAwardCategory
  award_label: string
  award_statement: string
  member_name: string
  work_title: string | null
  status: ActivityCertificateStatus
  issued_at: string
  revoked_at: string | null
  revocation_reason: string | null
  email_status: ActivityCertificateEmailStatus
  email_sent_at: string | null
  pdf_filename: string
  pdf_size_bytes: number
  verify_url: string
  download_path: string
}

export interface ActivityCertificateAdmin extends ActivityCertificateMember {
  activity_id: string
  member_id: string
  member_readable_id: string
  work_id: string | null
  issued_by: string
  issued_by_role: string
  template_version: string
  email_attempts: number
  email_last_error: string | null
}

export interface ActivityCertificateList {
  items: ActivityCertificateAdmin[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface ActivityCertificateEligibleParticipant {
  member_id: string
  member_readable_id: string
  member_name: string
  member_email: string | null
  participation_status: string
  role: string | null
  already_issued_awards: string[]
}

export interface ActivityCertificateEligibleList {
  activity_id: string
  activity_title: string
  items: ActivityCertificateEligibleParticipant[]
}

export interface ActivityCertificateIssueInput {
  activity_id: string
  member_id: string
  award_category: ActivityAwardCategory
  custom_award_label?: string | null
  custom_statement?: string | null
  work_id?: string | null
}

export interface ActivityCertificateBulkRecipientInput {
  member_id: string
  award_category?: ActivityAwardCategory | null
  custom_award_label?: string | null
  custom_statement?: string | null
  work_id?: string | null
}

export interface ActivityCertificateBulkIssueInput {
  activity_id: string
  award_category: ActivityAwardCategory
  recipients: ActivityCertificateBulkRecipientInput[]
}

export interface ActivityCertificateBulkSkipped {
  member_id: string
  certificate_id: string | null
  reason: string
}

export interface ActivityCertificateBulkFailed {
  member_id: string
  reason: string
}

export interface ActivityCertificateBulkResult {
  issued: ActivityCertificateAdmin[]
  skipped: ActivityCertificateBulkSkipped[]
  failed: ActivityCertificateBulkFailed[]
  issued_count: number
  skipped_count: number
  failed_count: number
}

export interface ActivityCertificateEmailResult {
  certificate_id: string
  email_status: ActivityCertificateEmailStatus
  email_sent_at: string | null
  message: string
}

export interface ActivityCertificateRevokePayload {
  reason: string
}

export interface ActivityCertificateTemplate {
  template_version: string
  heading: string
  presentation_line: string
  award_line: string
  scope_statement: string
  footer_note: string
  award_labels: Record<string, string>
  award_statements: Record<string, string>
  updated_by: string | null
  updated_at: string | null
}

export interface ActivityCertificateTemplateInput {
  heading: string
  presentation_line: string
  award_line: string
  scope_statement: string
  footer_note: string
  award_labels: Record<string, string>
  award_statements: Record<string, string>
}

export interface ActivityCertificateAuditEntry {
  action: ActivityCertificateAuditAction
  actor_id: string
  actor_role: string
  detail: string | null
  created_at: string
}

export interface PublicActivityCertificateWork {
  title: string
  url: string
}

export interface PublicActivityCertificate {
  certificate_id: string
  status: ActivityCertificateStatus
  issued_at: string
  member_name: string
  activity_title: string
  activity_type: string
  award_category: ActivityAwardCategory
  award_label: string
  award_statement: string
  work: PublicActivityCertificateWork | null
  revoked_at: string | null
  revocation_reason: string | null
}

export interface ActivityCertificateQuery {
  page?: number
  page_size?: number
  status?: ActivityCertificateStatus
  activity_id?: string
  member_id?: string
  award_category?: ActivityAwardCategory
}
