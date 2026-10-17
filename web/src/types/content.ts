/** Content domain types: clients, projects and testimonials (public + admin). */

export type ProjectType = 'client-work' | 'product' | 'experiment' | 'member-contribution'
export type ProjectStatus = 'draft' | 'published' | 'archived'
export type TestimonialStatus = 'pending' | 'approved' | 'rejected'

/** Public references always use slugs — internal Mongo ids are never exposed. */
export interface ContentRef {
  slug: string
  name: string
}

export interface PublicProject {
  slug: string
  name: string
  thumbnail_media_id: string | null
  gallery_media_ids: string[]
  description: string
  client: ContentRef | null
  category: string | null
  technologies: string[]
  live_url: string | null
  github_url: string | null
  project_type: ProjectType
  featured: boolean
  display_order: number
  completion_date: string | null
}

export interface PublicClient {
  slug: string
  name: string
  logo_media_id: string | null
  featured_image_media_id: string | null
  description: string
  website: string | null
  industry: string | null
  category: string | null
  featured: boolean
  display_order: number
  projects: ContentRef[]
}

export interface PublicTestimonial {
  id: string
  person_name: string
  role: string
  testimonial_text: string
  profile_image_media_id: string | null
  company: string | null
  rating: number
  featured: boolean
  display_order: number
  date: string | null
  client: ContentRef | null
}

export interface AdminClientRef {
  id: string
  slug: string
  name: string
}

export interface AdminProject extends Omit<PublicProject, 'client'> {
  id: string
  client_id: string | null
  client: AdminClientRef | null
  status: ProjectStatus
  created_at: string
  updated_at: string
}

export interface AdminClient extends Omit<PublicClient, 'projects'> {
  id: string
  project_ids: string[]
  created_at: string
  updated_at: string
}

export interface AdminTestimonial extends Omit<PublicTestimonial, 'client'> {
  id: string
  client_id: string | null
  client: AdminClientRef | null
  published: boolean
  status: TestimonialStatus
  created_at: string
  updated_at: string
}

type ContentQueryBase = Record<string, string | number | boolean | null | undefined>

export type ProjectQuery = {
  page?: number
  page_size?: number
  category?: string
  project_type?: ProjectType
  featured?: boolean
  sort?: string
  order?: 'asc' | 'desc'
} & ContentQueryBase

export type ClientQuery = {
  page?: number
  page_size?: number
  featured?: boolean
  sort?: string
  order?: 'asc' | 'desc'
} & ContentQueryBase

export type TestimonialQuery = {
  page?: number
  page_size?: number
  featured?: boolean
  status?: TestimonialStatus
  sort?: string
  order?: 'asc' | 'desc'
} & ContentQueryBase