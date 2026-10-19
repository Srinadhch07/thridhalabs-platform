/**
 * Public activities — programmes, hackathons and (invitation-only) projects.
 * Only published activities appear; featured activities surface first.
 */

import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { usePublicActivities } from '../../features/activities/hooks'
import { ActivityCard } from '../../components/public/ActivityCard'
import { SectionHeader } from '../../components/public/SectionHeader'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { EmptyState } from '../../components/ui/EmptyState'
import { usePageMeta, absolutePageUrl } from '../../lib/utils/seo'
import type { ActivityType } from '../../types/activity'

const FILTERS: Array<{ value: '' | ActivityType; label: string }> = [
  { value: '', label: 'All' },
  { value: 'programme', label: 'Programmes' },
  { value: 'hackathon', label: 'Hackathons' },
  { value: 'project', label: 'Projects' },
]

export default function ActivitiesPage() {
  const [params, setParams] = useSearchParams()
  const typeParam = params.get('type')
  const activeType: '' | ActivityType =
    typeParam === 'programme' || typeParam === 'hackathon' || typeParam === 'project'
      ? typeParam
      : ''
  const [page, setPage] = useState(1)

  const { data, loading, error, reload } = usePublicActivities({
    page,
    page_size: 12,
    sort: 'display_order',
    order: 'asc',
    activity_type: activeType || undefined,
  })

  usePageMeta({
    title: 'Activities — Thridha Labs',
    description: 'Programmes, hackathons and projects run by the lab.',
    canonical: absolutePageUrl('/activities'),
  })

  const items = data?.items ?? []

  function selectType(value: '' | ActivityType): void {
    setPage(1)
    setParams(value ? { type: value } : {})
  }

  return (
    <section className="section">
      <div className="shell">
        <SectionHeader level={1} tag="The lab / activities" title="Programmes, hackathons and projects." />

        <div className="filter-row" role="group" aria-label="Filter activities by type">
          <span className="filter-row__label">Filter</span>
          {FILTERS.map((filter) => (
            <button
              key={filter.value || 'all'}
              type="button"
              aria-pressed={activeType === filter.value}
              className="pill"
              onClick={() => selectType(filter.value)}
            >
              {filter.label}
            </button>
          ))}
        </div>

        {loading ? <ContentSkeleton rows={4} /> : null}
        {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}
        {!loading && !error && items.length === 0 ? (
          <EmptyState
            title="No activities yet"
            description="There are no published activities to show right now."
          />
        ) : null}

        {items.length > 0 ? (
          <ul className="activity-grid">
            {items.map((activity) => (
              <li key={activity.slug}>
                <ActivityCard activity={activity} />
              </li>
            ))}
          </ul>
        ) : null}

        {items.length > 0 && (data?.pages ?? 1) > 1 ? (
          <nav className="pagination" aria-label="Pagination">
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              disabled={page <= 1}
              onClick={() => setPage((value) => Math.max(1, value - 1))}
            >
              Prev
            </button>
            <span className="pagination__info">
              Page {data?.page ?? 1} of {data?.pages ?? 1}
            </span>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              disabled={page >= (data?.pages ?? 1)}
              onClick={() => setPage((value) => value + 1)}
            >
              Next
            </button>
          </nav>
        ) : null}
      </div>
    </section>
  )
}
