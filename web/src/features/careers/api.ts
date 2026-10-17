/** Careers feature API module — public settings/opportunities + admin CRUD. */

import { api } from '../../lib/api/client'
import type { StatusResponse } from '../../types/api'
import type {
  AdminCareersSettings,
  AdminOpportunity,
  OpportunityQuery,
  PublicCareersSettings,
  PublicOpportunity,
} from '../../types/careers'
import type { Paginated } from '../../types/pagination'

export function getPublicCareersSettings(): Promise<PublicCareersSettings> {
  return api.get<PublicCareersSettings>('/public/careers/settings')
}

export function getPublicOpportunities(
  query: OpportunityQuery = {},
): Promise<Paginated<PublicOpportunity>> {
  return api.get<Paginated<PublicOpportunity>>('/public/careers/opportunities', { query })
}

export function getAdminCareersSettings(): Promise<AdminCareersSettings> {
  return api.get<AdminCareersSettings>('/careers')
}

export function updateCareersSettings(payload: unknown): Promise<AdminCareersSettings> {
  return api.put<AdminCareersSettings>('/careers', payload)
}

export function listOpportunities(query: OpportunityQuery = {}): Promise<Paginated<AdminOpportunity>> {
  return api.get<Paginated<AdminOpportunity>>('/careers/opportunities', { query })
}

export function getOpportunity(opportunityId: string): Promise<AdminOpportunity> {
  return api.get<AdminOpportunity>(`/careers/opportunities/${opportunityId}`)
}

export function createOpportunity(payload: unknown): Promise<AdminOpportunity> {
  return api.post<AdminOpportunity>('/careers/opportunities', payload)
}

export function updateOpportunity(opportunityId: string, payload: unknown): Promise<AdminOpportunity> {
  return api.patch<AdminOpportunity>(`/careers/opportunities/${opportunityId}`, payload)
}

export function deleteOpportunity(opportunityId: string): Promise<StatusResponse> {
  return api.delete<StatusResponse>(`/careers/opportunities/${opportunityId}`)
}