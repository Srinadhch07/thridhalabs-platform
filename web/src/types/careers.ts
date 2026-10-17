/** Careers domain types: settings singleton + opportunities (public + admin). */

export type OpportunityType =
  | 'lab-member'
  | 'internship'
  | 'full-time'
  | 'part-time'
  | 'contract'
  | 'other'

export type WorkMode = 'remote' | 'on-site' | 'hybrid' | 'flexible'
export type OpportunityStatus = 'draft' | 'open' | 'closed'

/**
 * Public careers settings are intentionally sparse: `enabled` is plain system
 * state (like `maintenance_mode`) that the navigation needs to decide whether
 * the Careers link exists. The presentation fields are only exposed while the
 * singleton is enabled so a disabled careers page reveals nothing.
 */
export interface PublicCareersSettings {
  enabled: boolean
  heading: string | null
  description: string | null
  application_template: string | null
}

export interface AdminCareersSettings extends PublicCareersSettings {
  id: string
  application_email: string | null
  created_at: string
  updated_at: string
}

export interface PublicOpportunity {
  slug: string
  title: string
  type: OpportunityType
  custom_type: string | null
  description: string
  skills: string[]
  work_mode: WorkMode | null
  /** Resolved application email (override else global default) — null when unset. */
  application_email: string | null
}

export interface AdminOpportunity extends PublicOpportunity {
  id: string
  status: OpportunityStatus
  display_order: number
  created_at: string
  updated_at: string
}

export type OpportunityQuery = {
  page?: number
  page_size?: number
  status?: OpportunityStatus
  type?: OpportunityType
  work_mode?: WorkMode
  sort?: string
  order?: 'asc' | 'desc'
}