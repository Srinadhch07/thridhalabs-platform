import { api } from '../../../lib/api/client'
import type {
  AiSettings,
  AiSettingsTestPayload,
  AiSettingsTestResponse,
  AiSettingsUpdatePayload,
  AiSourceOverviewResponse,
  AiSummaryAdminResponse,
  AiSummaryDraftSaveRequest,
  AiSummaryGenerateRequest,
  AiSummaryListResponse,
} from '../../../types/ai'

const ADMIN_AI_SETTINGS = '/admin/ai/settings'
const ADMIN_AI_SOURCES = '/admin/ai/sources'
const ADMIN_AI_SUMMARIES = '/admin/ai/summaries'

export interface AiSummaryListQuery {
  page?: number
  page_size?: number
  activity_id?: string
  member_id?: string
  status?: 'draft' | 'published'
  sort?: 'updated_at' | 'published_at' | 'created_at'
  order?: 'asc' | 'desc'
}

export async function getAiSettings(): Promise<AiSettings> {
  return api.get<AiSettings>(ADMIN_AI_SETTINGS)
}

export async function updateAiSettings(payload: AiSettingsUpdatePayload): Promise<AiSettings> {
  return api.put<AiSettings>(ADMIN_AI_SETTINGS, payload)
}

export async function deleteAiSettingsKey(): Promise<AiSettings> {
  return api.delete<AiSettings>(`${ADMIN_AI_SETTINGS}/key`)
}

export async function testAiSettings(
  payload: AiSettingsTestPayload,
): Promise<AiSettingsTestResponse> {
  return api.post<AiSettingsTestResponse>(`${ADMIN_AI_SETTINGS}/test`, payload)
}

export async function getAiSources(): Promise<AiSourceOverviewResponse> {
  return api.get<AiSourceOverviewResponse>(ADMIN_AI_SOURCES)
}

export async function listAiSummaries(
  query: AiSummaryListQuery = {},
): Promise<AiSummaryListResponse> {
  const clean: Record<string, string | number | boolean> = {}
  if (query.page !== undefined) clean.page = query.page
  if (query.page_size !== undefined) clean.page_size = query.page_size
  if (query.activity_id) clean.activity_id = query.activity_id
  if (query.member_id) clean.member_id = query.member_id
  if (query.status) clean.status = query.status
  if (query.sort) clean.sort = query.sort
  if (query.order) clean.order = query.order
  return api.get<AiSummaryListResponse>(ADMIN_AI_SUMMARIES, { query: clean })
}

export async function generateAiSummary(
  payload: AiSummaryGenerateRequest,
): Promise<AiSummaryAdminResponse> {
  return api.post<AiSummaryAdminResponse>(`${ADMIN_AI_SUMMARIES}/generate`, payload)
}

export async function getAiSummary(id: string): Promise<AiSummaryAdminResponse> {
  return api.get<AiSummaryAdminResponse>(`${ADMIN_AI_SUMMARIES}/${id}`)
}

export async function saveAiSummaryDraft(
  id: string,
  payload: AiSummaryDraftSaveRequest,
): Promise<AiSummaryAdminResponse> {
  return api.patch<AiSummaryAdminResponse>(`${ADMIN_AI_SUMMARIES}/${id}`, payload)
}

export async function publishAiSummary(id: string): Promise<AiSummaryAdminResponse> {
  return api.post<AiSummaryAdminResponse>(`${ADMIN_AI_SUMMARIES}/${id}/publish`)
}

export async function unpublishAiSummary(id: string): Promise<AiSummaryAdminResponse> {
  return api.post<AiSummaryAdminResponse>(`${ADMIN_AI_SUMMARIES}/${id}/unpublish`)
}



