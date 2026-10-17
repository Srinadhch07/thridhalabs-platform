/** Member Work Showcase types (`/member/works` + `/public/members` APIs).
 *
 * The content document is a strict, versioned block schema — the API never
 * accepts or returns free HTML. Visibility and publication status are
 * independent; public exposure is only granted when the work is published,
 * its visibility is public, and the author's profile is public too.
 */

import type { CertificationStatus } from './certification'
import type { ProjectType } from './content'
import type { ProfileVisibility } from './member'

export type WorkVisibility = 'private' | 'members' | 'public'
export type WorkPublicationStatus =
  | 'draft'
  | 'pending_review'
  | 'changes_requested'
  | 'rejected'
  | 'published'
  | 'unpublished'
export type WorkReviewAction = 'approve' | 'request_changes' | 'reject'
export type WorkTemplate = 'blank-canvas' | 'project-showcase' | 'research' | 'creative-portfolio'
export type WorkSort = 'newest' | 'oldest' | 'title' | 'updated'

export interface ExternalLink {
  label: string
  url: string
}

export interface InlineRun {
  text: string
  bold?: boolean
  italic?: boolean
  code?: boolean
  link?: string | null
}

export interface ParagraphBlock {
  type: 'paragraph'
  spans: InlineRun[]
}

export interface HeadingBlock {
  type: 'heading'
  level: 2 | 3 | 4
  text: string
}

export interface ImageBlock {
  type: 'image'
  media_id: string
  caption?: string | null
  alt?: string | null
}

export interface ImageGalleryBlock {
  type: 'image_gallery'
  media_ids: string[]
}

export interface BulletedListBlock {
  type: 'bulleted_list'
  items: string[]
}

export interface NumberedListBlock {
  type: 'numbered_list'
  items: string[]
}

export interface QuoteBlock {
  type: 'quote'
  text: string
  attribution?: string | null
}

export interface CodeBlock {
  type: 'code'
  code: string
  language: string
}

export interface ExternalLinkBlock {
  type: 'external_link'
  label: string
  url: string
}

export interface DividerBlock {
  type: 'divider'
}

export type ContentBlock =
  | ParagraphBlock
  | HeadingBlock
  | ImageBlock
  | ImageGalleryBlock
  | BulletedListBlock
  | NumberedListBlock
  | QuoteBlock
  | CodeBlock
  | ExternalLinkBlock
  | DividerBlock

export type ContentBlockType = ContentBlock['type']

export interface ContentDocument {
  version: 1
  blocks: ContentBlock[]
}

/** Per-work certification state shown to the owner (and to reviewers). */
export interface WorkCertificationRef {
  request_id: string | null
  status: CertificationStatus | null
  version_reviewed: number | null
  reviewed_at: string | null
  feedback: string | null
  changed_since_review: boolean
  reviewable: boolean
}

/** Full member-owned view of a work. */
export interface MemberWork {
  id: string
  member_id: string
  title: string
  slug: string
  summary: string
  cover_media_id: string | null
  tags: string[]
  external_links: ExternalLink[]
  content: ContentDocument
  visibility: WorkVisibility
  publication_status: WorkPublicationStatus
  version: number
  profile_visibility: ProfileVisibility
  certification: WorkCertificationRef
  submitted_at: string | null
  review_feedback: string | null
  reviewed_at: string | null
  featured_on_projects: boolean
  featured_classification: ProjectType | null
  featured_at: string | null
  created_at: string
  updated_at: string
  published_at: string | null
}

/** List item — excludes the content document. */
export interface WorkCard {
  id: string
  member_id: string
  title: string
  slug: string
  summary: string
  cover_media_id: string | null
  tags: string[]
  visibility: WorkVisibility
  publication_status: WorkPublicationStatus
  version: number
  certification: WorkCertificationRef
  submitted_at: string | null
  review_feedback: string | null
  reviewed_at: string | null
  featured_on_projects: boolean
  featured_classification: ProjectType | null
  created_at: string
  updated_at: string
  published_at: string | null
}

export interface WorkList {
  items: WorkCard[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface WorkCreatePayload {
  title: string
  summary: string
  template?: WorkTemplate
  cover_media_id?: string | null
  tags?: string[]
  external_links?: ExternalLink[]
  content?: ContentDocument
  visibility?: WorkVisibility
}

export interface WorkUpdatePayload {
  title?: string
  summary?: string
  cover_media_id?: string | null
  tags?: string[]
  external_links?: ExternalLink[]
  content?: ContentDocument
  visibility?: WorkVisibility
}

export interface WorkQuery {
  page?: number
  page_size?: number
  status?: WorkPublicationStatus
  sort?: WorkSort
}

// --- Public surfaces --------------------------------------------------------

export interface WorkPublicAuthor {
  member_id: string
  display_name: string
  picture_media_id: string | null
}

export interface WorkPublic {
  slug: string
  title: string
  summary: string
  cover_media_id: string | null
  tags: string[]
  external_links: ExternalLink[]
  content: ContentDocument
  author: WorkPublicAuthor
  published_at: string
  updated_at: string
}

export interface WorkPublicCard {
  slug: string
  title: string
  summary: string
  cover_media_id: string | null
  tags: string[]
  published_at: string
}

export interface WorkPublicList {
  items: WorkPublicCard[]
}

// --- Publication review (admin) + official featuring ------------------------

export interface AdminWorkCard {
  id: string
  member_id: string
  member_name: string
  title: string
  slug: string
  summary: string
  cover_media_id: string | null
  tags: string[]
  visibility: WorkVisibility
  publication_status: WorkPublicationStatus
  version: number
  submitted_at: string | null
  review_feedback: string | null
  reviewed_at: string | null
  featured_on_projects: boolean
  featured_classification: ProjectType | null
  featured_at: string | null
  published_at: string | null
  created_at: string
  updated_at: string
}

export interface AdminWorkDetail extends AdminWorkCard {
  external_links: ExternalLink[]
  content: ContentDocument
}

export interface AdminWorkList {
  items: AdminWorkCard[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface AdminWorkQuery {
  page?: number
  page_size?: number
  status?: WorkPublicationStatus
  featured?: boolean
  sort?: 'created_at' | 'updated_at' | 'submitted_at' | 'published_at' | 'title'
  order?: 'asc' | 'desc'
}

export interface WorkReviewDecisionPayload {
  action: WorkReviewAction
  feedback?: string | null
}

export interface WorkFeaturePayload {
  featured: boolean
  classification?: ProjectType | null
}

/** A featured member work shown on the official Projects page. */
export interface FeaturedContribution {
  slug: string
  title: string
  summary: string
  cover_media_id: string | null
  tags: string[]
  classification: ProjectType
  featured_at: string | null
  published_at: string | null
  author: WorkPublicAuthor
}

export interface FeaturedContributionList {
  items: FeaturedContribution[]
}
