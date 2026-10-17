/**
 * Admin works — the publication-review queue. Lists member works with a status
 * filter (defaults to those awaiting review) and links into the review detail,
 * where decisions and official featuring are recorded.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAdminWorks } from '../../features/works/hooks'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { usePageMeta } from '../../lib/utils/seo'
import { WORK_STATUS_CHIP, WORK_STATUS_LABELS } from '../../features/works/status'
import { PageHeader } from '../../components/admin/PageHeader'
import { Pagination } from '../../components/admin/Pagination'
import { Select } from '../../components/form/Select'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { EmptyState } from '../../components/ui/EmptyState'
import type { WorkPublicationStatus } from '../../types/work'

function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString()
}

export default function AdminWorksPage() {
  usePageMeta({ title: 'Publication review — Admin — Thridha Labs' })

  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<'' | WorkPublicationStatus>('pending_review')
  const [featured, setFeatured] = useState<'' | 'true' | 'false'>('')

  const { data, loading, error, reload } = useAdminWorks({
    page,
    page_size: 20,
    status: status || undefined,
    featured: featured === '' ? undefined : featured === 'true',
  })
  useAdminSessionIssue(error)

  const items = data?.items ?? []

  return (
    <div>
      <PageHeader
        eyebrow="Review"
        title="Publication review"
        description="Works submitted by members for publication review, and works featured on the official Projects page."
      />

      <div className="admin-toolbar">
        <Select
          id="works-review-status"
          aria-label="Filter by status"
          placeholder="All statuses"
          options={Object.entries(WORK_STATUS_LABELS).map(([value, label]) => ({ value, label }))}
          value={status}
          onChange={(value) => {
            setStatus(value as '' | WorkPublicationStatus)
            setPage(1)
          }}
        />
        <Select
          id="works-review-featured"
          aria-label="Filter by featuring"
          placeholder="All works"
          options={[
            { value: 'true', label: 'Featured only' },
            { value: 'false', label: 'Not featured' },
          ]}
          value={featured}
          onChange={(value) => {
            setFeatured(value as '' | 'true' | 'false')
            setPage(1)
          }}
        />
      </div>

      {loading ? <ContentSkeleton rows={5} /> : null}
      {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}

      {!loading && !error && items.length === 0 ? (
        <EmptyState
          title="Nothing to review"
          description="Submissions awaiting publication review will appear here."
        />
      ) : null}

      {items.length > 0 ? (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Work</th>
                <th>Member</th>
                <th>Status</th>
                <th>Visibility</th>
                <th>Featured</th>
                <th>Submitted</th>
                <th className="admin-table__actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((work) => (
                <tr key={work.id}>
                  <td>
                    <Link className="admin-table__name" to={`/admin/works/${work.id}`}>
                      {work.title}
                    </Link>
                  </td>
                  <td>
                    {work.member_name}
                    <span className="admin-table__sub mono">{work.member_id}</span>
                  </td>
                  <td>
                    <span className={`chip ${WORK_STATUS_CHIP[work.publication_status]}`}>
                      {WORK_STATUS_LABELS[work.publication_status]}
                    </span>
                  </td>
                  <td style={{ textTransform: 'capitalize' }}>{work.visibility}</td>
                  <td>{work.featured_on_projects ? 'Featured' : '—'}</td>
                  <td>{formatDate(work.submitted_at)}</td>
                  <td className="admin-table__actions">
                    <Link className="btn btn--ghost btn--sm" to={`/admin/works/${work.id}`}>
                      Review
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {items.length > 0 ? (
        <Pagination page={data?.page ?? 1} pages={data?.pages ?? 1} total={data?.total ?? 0} onChange={setPage} />
      ) : null}
    </div>
  )
}
