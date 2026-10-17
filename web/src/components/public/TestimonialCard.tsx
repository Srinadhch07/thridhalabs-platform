/**
 * TestimonialCard — quote card with rating, attribution and an optional link
 * back to the related client.
 */

import { Link } from 'react-router-dom'
import type { PublicTestimonial } from '../../types/content'
import { resolveMediaUrl } from '../../lib/utils/mediaUrl'
import { StarLabel, Stars } from './Stars'

export interface TestimonialCardProps {
  item: PublicTestimonial
}

export function TestimonialCard({ item }: TestimonialCardProps) {
  const avatar = resolveMediaUrl(item.profile_image_media_id, 'thumb')
  return (
    <figure className="quote-card">
      <blockquote>{item.testimonial_text}</blockquote>
      <figcaption>
        {avatar && (
          <img
            className="quote-card__avatar"
            src={avatar}
            alt={`${item.person_name} portrait`}
            loading="lazy"
            decoding="async"
          />
        )}
        <div className="quote-meta">
          <span className="quote-meta__name">{item.person_name}</span>
          {item.role && <span className="quote-meta__role">{item.role}</span>}
          {item.company && <span className="quote-meta__role">{item.company}</span>}
        </div>
        <div className="stars">
          {item.rating > 0 && <Stars rating={item.rating} />}
          {item.rating > 0 && <StarLabel rating={item.rating} />}
        </div>
      </figcaption>
      {item.client && (
        <div className="quote-meta__role">
          <Link to="/clients">Built for {item.client.name}</Link>
        </div>
      )}
    </figure>
  )
}