/** Certificate types — issued certificates, verification and admin audit data.
 *
 * A certificate is issued for one approved certification request. The public
 * verification projection never includes private work content, member email,
 * storage keys or reviewer identity.
 */

import type { ContentDocument, ExternalLink, WorkPublicAuthor } from './work'

export type CertificateStatus = 'issued' | 'revoked'

export type CertificateEmailStatus = 'not_sent' | 'sent' | 'failed'

export interface CertificateMember {
  certificate_id: string
  request_id: string
  work_title: string
  work_slug: string
  member_name: string
  status: CertificateStatus
  issued_at: string
  revoked_at: string | null
  revocation_reason: string | null
  email_status: CertificateEmailStatus
  email_sent_at: string | null
  pdf_filename: string
  pdf_size_bytes: number
  verify_url: string
  download_path: string
}

export interface CertificateAdmin extends CertificateMember {
  issued_by: string
  issued_by_role: string
  decided_at: string | null
  template_version: string
  email_attempts: number
  email_last_error: string | null
}

export interface CertificateRef {
  certificate_id: string
  status: CertificateStatus
  issued_at: string
  email_status: CertificateEmailStatus
  work_title: string
  revoked_at: string | null
}

export interface PublicCertificate {
  certificate_id: string
  status: CertificateStatus
  issued_at: string
  member_name: string
  work_title: string
  work_url: string | null
  revoked_at: string | null
  revocation_reason: string | null
  /** The certified (snapshot) version of the work, when publicly showable. */
  work: PublicCertificateWork | null
}

/**
 * The certified snapshot of the work behind a certificate. Sourced from the
 * reviewed version, so it never reflects later edits to the live work.
 */
export interface PublicCertificateWork {
  title: string
  summary: string
  cover_media_id: string | null
  tags: string[]
  external_links: ExternalLink[]
  content: ContentDocument
  author: WorkPublicAuthor
  member_profile_url: string | null
  certified_at: string
  /** Link to the work's current published version, when one still exists. */
  current_work_url: string | null
  /** True when the work has been edited since the certified snapshot. */
  has_newer_version: boolean
}

export interface CertificateEmailResult {
  certificate_id: string
  email_status: CertificateEmailStatus
  email_sent_at: string | null
  message: string
}

export interface CertificateIssuePayload {
  request_id: string
}

export interface CertificateRevokePayload {
  reason: string
}

export interface CertificateQuery {
  page?: number
  page_size?: number
  status?: CertificateStatus
  member_id?: string
  request_id?: string
}
