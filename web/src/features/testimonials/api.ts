/** Testimonials feature API module — public listing/detail/submission + admin CRUD. */

import { api } from '../../lib/api/client'
import type { StatusResponse } from '../../types/api'
import type { AdminTestimonial, Paginated, PublicTestimonial, TestimonialQuery } from '../../types'

export function getPublicTestimonials(query: TestimonialQuery = {}): Promise<Paginated<PublicTestimonial>> {
  return api.get<Paginated<PublicTestimonial>>('/public/testimonials', { query })
}

export function getPublicTestimonial(id: string): Promise<PublicTestimonial> {
  return api.get<PublicTestimonial>(`/public/testimonials/${id}`)
}

export interface TestimonialSubmission {
  person_name: string
  role?: string
  company?: string | null
  testimonial_text: string
  rating?: number
}

export interface TestimonialSubmissionResult {
  message: string
}

/** Anonymous submission — always stored as pending; the server owns moderation. */
export function submitTestimonial(payload: TestimonialSubmission): Promise<TestimonialSubmissionResult> {
  return api.post<TestimonialSubmissionResult>('/public/testimonials', payload)
}

export function listTestimonials(query: TestimonialQuery = {}): Promise<Paginated<AdminTestimonial>> {
  return api.get<Paginated<AdminTestimonial>>('/testimonials', { query })
}

export function getTestimonial(id: string): Promise<AdminTestimonial> {
  return api.get<AdminTestimonial>(`/testimonials/${id}`)
}

export function createTestimonial(payload: unknown): Promise<AdminTestimonial> {
  return api.post<AdminTestimonial>('/testimonials', payload)
}

export function updateTestimonial(id: string, payload: unknown): Promise<AdminTestimonial> {
  return api.patch<AdminTestimonial>(`/testimonials/${id}`, payload)
}

export function deleteTestimonial(id: string): Promise<StatusResponse> {
  return api.delete<StatusResponse>(`/testimonials/${id}`)
}