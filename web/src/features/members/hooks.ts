/** Members hooks. */

import { useAsync } from '../../lib/hooks/useAsync'
import type { MemberListQuery } from '../../types/member'
import { getMember, getPublicMember, listMembers } from './api'

export function useAdminMembers(query: MemberListQuery = {}) {
  return useAsync(() => listMembers(query), [JSON.stringify(query)])
}

export function useAdminMember(memberId: string | undefined) {
  return useAsync(
    async () => {
      if (!memberId) throw new Error('Missing member id')
      return getMember(memberId)
    },
    [memberId],
  )
}

export function usePublicMember(memberId: string | undefined) {
  return useAsync(
    async () => {
      if (!memberId) throw new Error('Missing member id')
      return getPublicMember(memberId)
    },
    [memberId],
  )
}