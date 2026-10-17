/** Certifications feature API module — member submissions + admin review. */

import { api } from '../../lib/api/client'
import type { QueryParams } from '../../lib/api/client'
import type {
  CertificationApplyPayload,
  CertificationDecisionPayload,
  CertificationDetail,
  CertificationList,
  CertificationQuery,
} from '../../types/certification'

// --- Member -----------------------------------------------------------------

export function applyCertification(payload: CertificationApplyPayload): Promise<CertificationDetail> {
  return api.post<CertificationDetail>('/member/certifications', payload)
}

export function listMemberCertifications(
  query: CertificationQuery = {},
): Promise<CertificationList> {
  return api.get<CertificationList>('/member/certifications', { query: query as QueryParams })
}

export function getMemberCertification(requestId: string): Promise<CertificationDetail> {
  return api.get<CertificationDetail>(`/member/certifications/${requestId}`)
}

// --- Admin ------------------------------------------------------------------

export function listAdminCertifications(
  query: CertificationQuery = {},
): Promise<CertificationList> {
  return api.get<CertificationList>('/admin/certifications', { query: query as QueryParams })
}

export function getAdminCertification(requestId: string): Promise<CertificationDetail> {
  return api.get<CertificationDetail>(`/admin/certifications/${requestId}`)
}

export function decideCertification(
  requestId: string,
  payload: CertificationDecisionPayload,
): Promise<CertificationDetail> {
  return api.post<CertificationDetail>(`/admin/certifications/${requestId}/decision`, payload)
}
