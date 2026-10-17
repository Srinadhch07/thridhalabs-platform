/** Testimonials hooks. */

import { useAsync } from '../../lib/hooks/useAsync'
import { getTestimonial, getPublicTestimonials, listTestimonials } from './api'
import type { TestimonialQuery } from '../../types/content'

export function usePublicTestimonials(query: TestimonialQuery = {}) {
  return useAsync(() => getPublicTestimonials(query), [JSON.stringify(query)])
}

export function useAdminTestimonials(query: TestimonialQuery = {}) {
  return useAsync(() => listTestimonials(query), [JSON.stringify(query)])
}

export function useAdminTestimonial(testimonialId: string | undefined) {
  return useAsync(
    async () => {
      if (!testimonialId) throw new Error('Missing testimonial id')
      return getTestimonial(testimonialId)
    },
    [testimonialId],
  )
}