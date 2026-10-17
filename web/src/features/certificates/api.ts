/** Certificates feature API module — issuance, delivery, download, verification. */

import { api, downloadFile } from '../../lib/api/client'
import type { DownloadedFile, QueryParams } from '../../lib/api/client'
import type { Paginated } from '../../types/pagination'
import type {
  CertificateAdmin,
  CertificateEmailResult,
  CertificateIssuePayload,
  CertificateMember,
  CertificateQuery,
  CertificateRevokePayload,
  PublicCertificate,
} from '../../types/certificate'

// --- Member -----------------------------------------------------------------

export function listMemberCertificates(
  query: CertificateQuery = {},
): Promise<Paginated<CertificateMember>> {
  return api.get<Paginated<CertificateMember>>('/member/certificates', {
    query: query as QueryParams,
  })
}

export function getMemberCertificate(certificateId: string): Promise<CertificateMember> {
  return api.get<CertificateMember>(`/member/certificates/${certificateId}`)
}

export function downloadMemberCertificate(certificateId: string): Promise<DownloadedFile> {
  return downloadFile(`/member/certificates/${certificateId}/download`)
}

// --- Admin ------------------------------------------------------------------

export function issueCertificate(payload: CertificateIssuePayload): Promise<CertificateAdmin> {
  return api.post<CertificateAdmin>('/admin/certificates', payload)
}

export function listAdminCertificates(
  query: CertificateQuery = {},
): Promise<Paginated<CertificateAdmin>> {
  return api.get<Paginated<CertificateAdmin>>('/admin/certificates', {
    query: query as QueryParams,
  })
}

export function getAdminCertificate(certificateId: string): Promise<CertificateAdmin> {
  return api.get<CertificateAdmin>(`/admin/certificates/${certificateId}`)
}

export function downloadAdminCertificate(certificateId: string): Promise<DownloadedFile> {
  return downloadFile(`/admin/certificates/${certificateId}/download`)
}

export function emailCertificate(certificateId: string): Promise<CertificateEmailResult> {
  return api.post<CertificateEmailResult>(`/admin/certificates/${certificateId}/email`)
}

export function revokeCertificate(
  certificateId: string,
  payload: CertificateRevokePayload,
): Promise<CertificateAdmin> {
  return api.post<CertificateAdmin>(`/admin/certificates/${certificateId}/revoke`, payload)
}

// --- Public -----------------------------------------------------------------

export function verifyCertificate(certificateId: string): Promise<PublicCertificate> {
  return api.get<PublicCertificate>(`/public/certificates/${certificateId}`)
}
