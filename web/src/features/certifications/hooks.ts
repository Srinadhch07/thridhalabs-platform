/** Certifications hooks. */

import { useAsync } from '../../lib/hooks/useAsync'
import type { CertificationQuery } from '../../types/certification'
import {
  getAdminCertification,
  getMemberCertification,
  listAdminCertifications,
  listMemberCertifications,
} from './api'

export function useMemberCertifications(query: CertificationQuery = {}) {
  return useAsync(() => listMemberCertifications(query), [JSON.stringify(query)])
}

export function useMemberCertification(requestId: string | undefined) {
  return useAsync(
    async () => {
      if (!requestId) throw new Error('Missing request id')
      return getMemberCertification(requestId)
    },
    [requestId],
  )
}

export function useAdminCertifications(query: CertificationQuery = {}) {
  return useAsync(() => listAdminCertifications(query), [JSON.stringify(query)])
}

export function useAdminCertification(requestId: string | undefined) {
  return useAsync(
    async () => {
      if (!requestId) throw new Error('Missing request id')
      return getAdminCertification(requestId)
    },
    [requestId],
  )
}
