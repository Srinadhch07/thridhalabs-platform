/** Certificates hooks. */

import { useAsync } from '../../lib/hooks/useAsync'
import type { CertificateQuery } from '../../types/certificate'
import {
  getAdminCertificate,
  getMemberCertificate,
  listAdminCertificates,
  listMemberCertificates,
  verifyCertificate,
} from './api'

export function useMemberCertificates(query: CertificateQuery = {}) {
  return useAsync(() => listMemberCertificates(query), [JSON.stringify(query)])
}

export function useMemberCertificate(certificateId: string | undefined) {
  return useAsync(
    async () => {
      if (!certificateId) throw new Error('Missing certificate id')
      return getMemberCertificate(certificateId)
    },
    [certificateId],
  )
}

export function useAdminCertificates(query: CertificateQuery = {}) {
  return useAsync(() => listAdminCertificates(query), [JSON.stringify(query)])
}

export function useAdminCertificate(certificateId: string | undefined) {
  return useAsync(
    async () => {
      if (!certificateId) throw new Error('Missing certificate id')
      return getAdminCertificate(certificateId)
    },
    [certificateId],
  )
}

export function usePublicCertificate(certificateId: string | undefined) {
  return useAsync(
    async () => {
      if (!certificateId) throw new Error('Missing certificate id')
      return verifyCertificate(certificateId)
    },
    [certificateId],
  )
}
