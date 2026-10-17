/** Careers hooks. */

import { useAsync } from '../../lib/hooks/useAsync'
import type { OpportunityQuery } from '../../types/careers'
import type { Paginated } from '../../types/pagination'
import type { PublicOpportunity } from '../../types/careers'
import {
  getAdminCareersSettings,
  getOpportunity,
  getPublicCareersSettings,
  getPublicOpportunities,
  listOpportunities,
} from './api'

export function usePublicCareersSettings() {
  return useAsync(() => getPublicCareersSettings(), [])
}

const EMPTY_OPPORTUNITIES: Paginated<PublicOpportunity> = {
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
  pages: 0,
}

/**
 * Public opportunities — `skip` avoids a doomed request while careers are
 * disabled (the backend 404s that endpoint) and still refetches the moment
 * the singleton is enabled.
 */
export function usePublicOpportunities(query: OpportunityQuery = {}, skip = false) {
  return useAsync(
    () => (skip ? Promise.resolve(EMPTY_OPPORTUNITIES) : getPublicOpportunities(query)),
    [JSON.stringify(query), skip],
  )
}

export function useAdminCareersSettings() {
  return useAsync(() => getAdminCareersSettings(), [])
}

export function useAdminOpportunities(query: OpportunityQuery = {}) {
  return useAsync(() => listOpportunities(query), [JSON.stringify(query)])
}

export function useAdminOpportunity(opportunityId: string | undefined) {
  return useAsync(
    async () => {
      if (!opportunityId) throw new Error('Missing opportunity id')
      return getOpportunity(opportunityId)
    },
    [opportunityId],
  )
}