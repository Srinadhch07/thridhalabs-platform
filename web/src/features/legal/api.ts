import { api } from '../../lib/api/client'

export type LegalStatus = 'draft' | 'published'
export type LegalSlug = 'privacy-policy' | 'terms-and-conditions' | 'cookie-policy'

export interface LegalAdminItem {
  id: string
  slug: LegalSlug
  title: string
  content_markdown: string
  status: LegalStatus
  created_at: string
  updated_at: string
  published_at: string | null
}

export interface LegalPublicItem {
  slug: LegalSlug
  title: string
  content_markdown: string
  updated_at: string | null
  published_at: string | null
}

export async function listLegal(): Promise<LegalAdminItem[]> {
  const res = await api.get<{ items: LegalAdminItem[] }>('/legal')
  return res.items
}

export async function getLegal(slug: LegalSlug): Promise<LegalAdminItem> {
  return api.get<LegalAdminItem>(`/legal/${slug}`)
}

export async function saveLegalDraft(
  slug: LegalSlug,
  payload: { title?: string | null; content_markdown: string; expected_updated_at?: string | null },
): Promise<LegalAdminItem> {
  return api.put<LegalAdminItem>(`/legal/${slug}/draft`, payload)
}

export async function publishLegal(
  slug: LegalSlug,
  payload: { title?: string | null; content_markdown?: string | null; expected_updated_at?: string | null },
): Promise<LegalAdminItem> {
  return api.post<LegalAdminItem>(`/legal/${slug}/publish`, payload)
}

export async function getPublicLegal(slug: LegalSlug): Promise<LegalPublicItem> {
  return api.get<LegalPublicItem>(`/public/legal/${slug}`)
}
