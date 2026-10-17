/**
 * AI Summarization types (match backend schemas).
 */

export type AiSummaryState =
  | 'empty'
  | 'draft'
  | 'published'
  | 'outdated'
  | 'failed'

export interface AiSummarySourceRef {
  report_id: string
  version: number
  submitted_at: string
}

export interface AiSummaryGenerationEntry {
  at: string
  model: string
  status: 'ok' | 'error'
  error_code: string | null
  error_message: string | null
}

export interface AiSummaryAdminResponse {
  id: string
  activity_id: string
  activity_slug: string
  activity_title: string
  member_id: string
  member_readable_id: string
  member_name: string
  state: AiSummaryState

  draft_content: string | null
  draft_model: string | null
  draft_generated_at: string | null
  draft_reviewed: boolean
  draft_outdated: boolean

  published_content: string | null
  published_model: string | null
  published_at: string | null

  source_reports: AiSummarySourceRef[]
  source_report_count: number
  outdated: boolean
  last_error_code: string | null
  last_error_message: string | null
  generations: AiSummaryGenerationEntry[]
  updated_at: string
}

export interface AiSummaryListResponse {
  items: AiSummaryAdminResponse[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface AiSourceMemberOption {
  member_id: string
  member_readable_id: string
  member_name: string
  approved_count: number
  summary_id: string | null
  summary_state: AiSummaryState | null
}

export interface AiSourceProjectOption {
  activity_id: string
  slug: string
  title: string
  approved_count: number
  members: AiSourceMemberOption[]
}

export interface AiSourceOverviewResponse {
  projects: AiSourceProjectOption[]
}

export interface AiSettings {
  provider: string
  model: string
  enabled: boolean
  configured: boolean
  encryption_available: boolean
  key_hint: string | null
  key_set_at: string | null
  key_set_by_name: string | null
  last_test_at: string | null
  last_test_ok: boolean | null
  last_test_error: string | null
  updated_at: string
}

export interface AiSettingsUpdatePayload {
  api_key?: string
  model?: string
  enabled?: boolean
}

export interface AiSettingsTestPayload {
  api_key?: string
  model?: string
}

export interface AiSettingsTestResponse {
  ok: boolean
  model: string
  models_available: number | null
  model_available: boolean | null
  latency_ms: number | null
  error_code: string | null
  error_message: string | null
}

export interface AiSummaryGenerateRequest {
  activity_id: string
  member_id: string
}

export interface AiSummaryDraftSaveRequest {
  draft_content: string
}

/** Published summary as it appears in the member contribution history. */
export interface ContributionSummary {
  id: string
  content: string
  model: string | null
  published_at: string
  source_report_count: number
  source_report_ids: string[]
}
