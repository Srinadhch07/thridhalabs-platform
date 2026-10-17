/** Media library types (Phase 3 API). */

export type MediaType = 'image'
export type MediaVariantName = 'original' | 'thumb' | 'md' | 'lg'

export interface MediaVariant {
  name: string
  object_key: string
  width: number
  height: number
  size_bytes: number
  mime_type: string
}

export interface Media {
  id: string
  original_name: string
  format: string
  mime_type: string
  media_type: MediaType
  size_bytes: number
  width: number
  height: number
  checksum: string
  storage_mode: string
  variants: MediaVariant[]
  /** Variant name -> file URL (relative to the API, or absolute for S3). */
  urls: Record<string, string>
  created_by: string
  created_at: string
  updated_at: string
}

export type MediaQuery = {
  page?: number
  page_size?: number
  sort?: 'newest' | 'oldest'
}