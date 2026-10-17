/**
 * Testimonials page — public reputation signal from the testimonials API,
 * plus an anonymous submission form (server-moderated: new entries stay
 * pending until an admin approves them, so nothing submitted here ever
 * appears immediately).
 */

import { useState } from 'react'
import { PageHeader } from '../../components/public/PageHeader'
import { Reveal } from '../../components/public/Reveal'
import { TestimonialCard } from '../../components/public/TestimonialCard'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { usePublicTestimonials } from '../../features/testimonials/hooks'
import { submitTestimonial } from '../../features/testimonials/api'
import { getErrorMessage, isApiError } from '../../lib/errors/ApiError'
import { absolutePageUrl, useBrandingOgImage, usePageMeta } from '../../lib/utils/seo'

function SubmissionForm() {
  const [personName, setPersonName] = useState('')
  const [role, setRole] = useState('')
  const [company, setCompany] = useState('')
  const [text, setText] = useState('')
  const [rating, setRating] = useState('5')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)

  if (submitted) {
    return (
      <div className="submit-thanks" role="status">
        <p className="eyebrow">Received</p>
        <h3>Thank you for sharing your experience!</h3>
        <p>Your testimonial has been submitted for review.</p>
      </div>
    )
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    if (!personName.trim() || !text.trim()) {
      setError('Please add your name and your testimonial.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await submitTestimonial({
        person_name: personName.trim(),
        role: role.trim(),
        company: company.trim() || null,
        testimonial_text: text.trim(),
        rating: Number(rating),
      })
      setSubmitted(true)
    } catch (caught) {
      if (isApiError(caught) && caught.status === 503) {
        setError('The lab is briefly offline for maintenance — please try again soon.')
      } else {
        setError(getErrorMessage(caught, 'Could not submit your testimonial. Please try again.'))
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="submit-form" onSubmit={handleSubmit} noValidate>
      <div className="submit-form__row">
        <label className="submit-form__field">
          <span>Name</span>
          <input
            type="text"
            value={personName}
            onChange={(event) => setPersonName(event.target.value)}
            placeholder="Ada Lovelace"
            autoComplete="name"
            required
          />
        </label>
        <label className="submit-form__field">
          <span>Role / Title</span>
          <input
            type="text"
            value={role}
            onChange={(event) => setRole(event.target.value)}
            placeholder="Partner"
            autoComplete="organization-title"
          />
        </label>
      </div>
      <div className="submit-form__row">
        <label className="submit-form__field">
          <span>Company / Organization (optional)</span>
          <input
            type="text"
            value={company}
            onChange={(event) => setCompany(event.target.value)}
            placeholder="Acme Co"
            autoComplete="organization"
          />
        </label>
        <label className="submit-form__field">
          <span>Rating</span>
          <select value={rating} onChange={(event) => setRating(event.target.value)}>
            {[5, 4, 3, 2, 1].map((value) => (
              <option key={value} value={String(value)}>
                {'★'.repeat(value)} ({value}/5)
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className="submit-form__field">
        <span>Testimonial</span>
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={4}
          placeholder="What did working with Thridha Labs make possible?"
          required
        />
      </label>
      {error ? (
        <p className="submit-form__error" role="alert">
          {error}
        </p>
      ) : null}
      <button type="submit" className="btn btn--primary" disabled={submitting}>
        {submitting ? 'Submitting…' : 'Submit testimonial'}
      </button>
    </form>
  )
}

export default function TestimonialsPage() {
  const { data, loading, error, reload } = usePublicTestimonials({ sort: 'display_order', order: 'asc' })
  const brandingOgImage = useBrandingOgImage()

  usePageMeta({
    title: 'Testimonials — Thridha Labs',
    description: 'What people say about working with Thridha Labs.',
    canonical: absolutePageUrl('/testimonials'),
    ogImage: brandingOgImage,
  })

  const items = data?.items ?? []

  return (
    <>
      <PageHeader
        eyebrow="Testimonials / signal"
        title="What people say"
        lede="Signal from the people we work with. No invented quotes — only what has been logged in the lab."
        meta={
          <p className="eyebrow" style={{ marginBottom: 0 }}>
            {data ? `${items.length.toString().padStart(2, '0')} signals on file` : 'Indexing…'}
          </p>
        }
      />

      <div className="shell" style={{ paddingBlock: 'var(--space-7)' }}>
        {loading ? (
          <ContentSkeleton rows={6} />
        ) : error ? (
          <ErrorState title="Unable to load testimonials" error={error} onRetry={reload} />
        ) : items.length === 0 ? (
          <EmptyState
            title="No testimonials yet"
            description="Testimonials will appear here once reviewed and approved."
          />
        ) : (
          <div className="quote-grid">
            {items.map((item) => (
              <Reveal key={item.id} className="reveal--grid">
                <TestimonialCard item={item} />
              </Reveal>
            ))}
          </div>
        )}
      </div>

      <div className="shell" style={{ paddingBottom: 'var(--space-8)' }}>
        <section className="share-section" aria-labelledby="share-heading">
          <p className="eyebrow">Your turn</p>
          <h2 id="share-heading">Share your experience</h2>
          <p className="share-section__lede">
            Worked with the lab? Every submission is reviewed before anything appears here.
          </p>
          <SubmissionForm />
        </section>
      </div>
    </>
  )
}