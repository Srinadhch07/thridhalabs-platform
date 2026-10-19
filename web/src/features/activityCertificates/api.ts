/** Activity certificates feature API — issuance, bulk issue, delivery, template,
 * revocation and public verification. Mirrors the certificates feature module.
 */

import { api, downloadFile } from '../../lib/api/client'
import type { DownloadedFile, QueryParams } from '../../lib/api/client'
import type {
  ActivityCertificateAdmin,
  ActivityCertificateAuditEntry,
  ActivityCertificateBulkIssueInput,
  ActivityCertificateBulkResult,
  ActivityCertificateEmailResult,
  ActivityCertificateEligibleList,
  ActivityCertificateIssueInput,
  ActivityCertificateList,
  ActivityCertificateQuery,
  ActivityCertificateRevokePayload,
  ActivityCertificateTemplate,
  ActivityCertificateTemplateInput,
  PublicActivityCertificate,
} from '../../types/activityCertificate'

// --- Admin ------------------------------------------------------------------
export function listAdminActivityCertificates(
  query: ActivityCertificateQuery = {},
): Promise<ActivityCertificateList> {
  return api.get<ActivityCertificateList>('/admin/activity-certificates', {
    query: query as QueryParams,
  })
}

export function getAdminActivityCertificate(
  certificateId: string,
): Promise<ActivityCertificateAdmin> {
  return api.get<ActivityCertificateAdmin>(`/admin/activity-certificates/${certificateId}`)
}

export function listEligibleParticipants(
  activityId: string,
): Promise<ActivityCertificateEligibleList> {
  return api.get<ActivityCertificateEligibleList>('/admin/activity-certificates/eligible', {
    query: { activity_id: activityId },
  })
}

export function issueActivityCertificate(
  payload: ActivityCertificateIssueInput,
): Promise<ActivityCertificateAdmin> {
  return api.post<ActivityCertificateAdmin>('/admin/activity-certificates', payload)
}

export function bulkIssueActivityCertificates(
  payload: ActivityCertificateBulkIssueInput,
): Promise<ActivityCertificateBulkResult> {
  return api.post<ActivityCertificateBulkResult>('/admin/activity-certificates/bulk', payload)
}

export function downloadAdminActivityCertificate(
  certificateId: string,
): Promise<DownloadedFile> {
  return downloadFile(`/admin/activity-certificates/${certificateId}/download`)
}

export function emailActivityCertificate(
  certificateId: string,
): Promise<ActivityCertificateEmailResult> {
  return api.post<ActivityCertificateEmailResult>(
    `/admin/activity-certificates/${certificateId}/email`,
  )
}

export function revokeActivityCertificate(
  certificateId: string,
  payload: ActivityCertificateRevokePayload,
): Promise<ActivityCertificateAdmin> {
  return api.post<ActivityCertificateAdmin>(
    `/admin/activity-certificates/${certificateId}/revoke`,
    payload,
  )
}

export function listActivityCertificateAudit(
  certificateId: string,
): Promise<ActivityCertificateAuditEntry[]> {
  return api.get<ActivityCertificateAuditEntry[]>(
    `/admin/activity-certificates/${certificateId}/audit`,
  )
}

export function getActivityCertificateTemplate(): Promise<ActivityCertificateTemplate> {
  return api.get<ActivityCertificateTemplate>('/admin/activity-certificates/template')
}

export function updateActivityCertificateTemplate(
  payload: ActivityCertificateTemplateInput,
): Promise<ActivityCertificateTemplate> {
  return api.put<ActivityCertificateTemplate>('/admin/activity-certificates/template', payload)
}

// --- Public -----------------------------------------------------------------
export function verifyActivityCertificate(
  certificateId: string,
): Promise<PublicActivityCertificate> {
  return api.get<PublicActivityCertificate>(
    `/public/activity-certificates/${certificateId}`,
  )
}
