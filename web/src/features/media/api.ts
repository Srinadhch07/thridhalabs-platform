/** Media feature API module — authenticated media library endpoints. */

import { api, upload } from '../../lib/api/client'
import { resolveMediaUrl } from '../../lib/utils/mediaUrl'
import type { MediaQuery, Media, Paginated } from '../../types'
import type { StatusResponse } from '../../types/api'

export function listMedia(query: MediaQuery = {}): Promise<Paginated<Media>> {
  return api.get<Paginated<Media>>('/media', { query })
}

export function getMedia(mediaId: string): Promise<Media> {
  return api.get<Media>(`/media/${mediaId}`)
}

/**
 * Resolve a preview URL for a single referenced media id in admin context.
 *
 * Uses the authenticated media lookup so the preview points at the controlled
 * file route (works for both local and S3 storage) without listing the library.
 */
export async function resolveAdminMediaPreviewUrl(
  mediaId: string,
  variant = 'thumb',
): Promise<string | null> {
  const media = await getMedia(mediaId)
  return resolveMediaUrl(media, variant) ?? resolveMediaUrl(media)
}

export function uploadMedia(file: File): Promise<Media> {
  return upload<Media>('/media', file)
}

export function deleteMedia(mediaId: string): Promise<StatusResponse> {
  return api.delete<StatusResponse>(`/media/${mediaId}`)
}

// --- Member-scoped media ----------------------------------------------------

export function listMemberMedia(query: MediaQuery = {}): Promise<Paginated<Media>> {
  return api.get<Paginated<Media>>('/member/media', { query })
}

export function uploadMemberMedia(file: File): Promise<Media> {
  return upload<Media>('/member/media', file)
}