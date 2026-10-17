/**
 * ActivityCarousel — homepage strip of featured, published activities.
 *
 * Only published + featured activities are ever returned by the public
 * endpoint, so drafts/cancelled/archived never leak here. Renders nothing when
 * there is no featured activity; on error, a section-level retry.
 *
 * The track is a native horizontal scroller (touch/swipe on mobile) with
 * accessible previous/next controls. Arrow scrolling respects the user's
 * reduced-motion preference; there is no automatic scrolling.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { usePublicActivities } from '../../features/activities/hooks'
import { ActivityCard } from './ActivityCard'
import { SectionHeader } from './SectionHeader'
import { ErrorState } from '../ui/ErrorState'

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function ActivityCarousel() {
  const { data, error, reload } = usePublicActivities({
    featured: true,
    sort: 'display_order',
    order: 'asc',
    page_size: 12,
  })

  const trackRef = useRef<HTMLUListElement>(null)
  const [canPrev, setCanPrev] = useState(false)
  const [canNext, setCanNext] = useState(false)

  const items = data?.items ?? []
  const hasItems = items.length > 0

  const updateArrows = useCallback(() => {
    const el = trackRef.current
    if (!el) return
    setCanPrev(el.scrollLeft > 4)
    setCanNext(el.scrollLeft + el.clientWidth < el.scrollWidth - 4)
  }, [])

  useEffect(() => {
    updateArrows()
  }, [items.length, updateArrows])

  function scrollByPage(direction: -1 | 1): void {
    const el = trackRef.current
    if (!el) return
    el.scrollBy({
      left: direction * el.clientWidth * 0.9,
      behavior: prefersReducedMotion() ? 'auto' : 'smooth',
    })
  }

  if (error) {
    return (
      <section className="section">
        <div className="shell">
          <SectionHeader tag="Programmes" title="Open programmes & hackathons." />
          <ErrorState title="Unable to load activities" error={error} onRetry={reload} />
        </div>
      </section>
    )
  }

  if (!hasItems) return null

  return (
    <section className="section" aria-labelledby="activities-title">
      <div className="shell">
        <SectionHeader
          id="activities-title"
          tag="Programmes"
          title="Open programmes & hackathons."
          action={{ to: '/activities', label: 'All activities' }}
        />
        {items.length > 1 ? (
          <div className="activity-carousel__nav">
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              aria-label="Previous activities"
              aria-controls="activity-carousel-track"
              disabled={!canPrev}
              onClick={() => scrollByPage(-1)}
            >
              ← Prev
            </button>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              aria-label="Next activities"
              aria-controls="activity-carousel-track"
              disabled={!canNext}
              onClick={() => scrollByPage(1)}
            >
              Next →
            </button>
          </div>
        ) : null}
        <ul
          id="activity-carousel-track"
          ref={trackRef}
          className="activity-carousel"
          aria-label="Featured activities"
          onScroll={updateArrows}
        >
          {items.map((activity) => (
            <li key={activity.slug} className="activity-carousel__item">
              <ActivityCard activity={activity} compact />
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
