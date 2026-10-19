/** Activity certificates hooks. */

import { useAsync } from '../../lib/hooks/useAsync'
import type { ActivityCertificateQuery } from '../../types/activityCertificate'
import {
  getAdminActivityCertificate,
  getActivityCertificateTemplate,
  listAdminActivityCertificates,
  listEligibleParticipants,
  verifyActivityCertificate,
} from './api'

export function useAdminActivityCertificates(query: ActivityCertificateQuery = {}) {
  return useAsync(() => listAdminActivityCertificates(query), [JSON.stringify(query)])
}

export function useAdminActivityCertificate(certificateId: string | undefined) {
  return useAsync(
    async () => {
      if (!certificateId) throw new Error('Missing activity certificate id')
      return getAdminActivityCertificate(certificateId)
    },
    [certificateId],
  )
}

export function useEligibleParticipants(activityId: string | undefined) {
  return useAsync(
    async () => {
      if (!activityId) throw new Error('Missing activity id')
      return listEligibleParticipants(activityId)
    },
    [activityId],
  )
}

export function useActivityCertificateTemplate() {
  return useAsync(() => getActivityCertificateTemplate(), [])
}

export function usePublicActivityCertificate(certificateId: string | undefined) {
  return useAsync(
    async () => {
      if (!certificateId) throw new Error('Missing activity certificate id')
      return verifyActivityCertificate(certificateId)
    },
    [certificateId],
  )
}
