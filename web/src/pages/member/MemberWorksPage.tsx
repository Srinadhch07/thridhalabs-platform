/**
 * Member works — the Work Showcase dashboard: the member's own works with
 * publication/visibility state, filtering, and a link into each editor.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMemberWorks } from '../../features/works/hooks'
import { useMemberSessionIssue } from '../../lib/hooks/useMemberSession'
import { usePageMeta } from '../../lib/utils/seo'
import { WORK_STATUS_LABELS } from '../../features/works/status'
import { MemberPageHeader } from '../../components/member/MemberPageHeader'
import { MemberEmptyState } from '../../components/member/MemberEmptyState'
import { WorkCard } from '../../components/works/WorkCard'
import { Select } from '../../components/form/Select'
import { Pagination } from '../../components/admin/Pagination'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import type { WorkPublicationStatus, WorkSort } from '../../types/work'

const SORT_LABELS: Record<WorkSort, string> = {
  newest: 'Newest first',
  oldest: 'Oldest first',
  title: 'Title A–Z',
  updated: 'Recently updated',
}

export default function MemberWorksPage() {
  usePageMeta({ title: 'Work Showcase — Member portal — Thridha Labs' })

  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<'' | WorkPublicationStatus>('')
  const [sort, setSort] = useState<WorkSort>('newest')

  const { data, loading, error, reload } = useMemberWorks({
    page,
    page_size: 12,
    sort,
    status: status || undefined,
  })
  useMemberSessionIssue(error)

  const items = data?.items ?? []

  return (
    <div className="member-page">
      <MemberPageHeader
        title="Work Showcase"
        description="Build, publish and share your work with the lab and the world."
        actions={
          <Link className="btn btn--primary" to="/member/works/new">
            New work
          </Link>
        }
      />

      <div className="member-toolbar">
        <Select
          id="works-status"
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
          id="works-sort"
          aria-label="Sort works"
          options={Object.entries(SORT_LABELS).map(([value, label]) => ({ value, label }))}
          value={sort}
          onChange={(value) => {
            setSort(value as WorkSort)
            setPage(1)
          }}
        />
      </div>

      {loading ? <ContentSkeleton rows={4} /> : null}
      {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}

      {!loading && !error && items.length === 0 ? (
        status ? (
          <MemberEmptyState
            title="No works match that filter"
            description="Try a different publication status."
          />
        ) : (
          <MemberEmptyState
            title="No works yet"
            description="Create your first work to start building your showcase."
            action={
              <Link className="btn btn--primary" to="/member/works/new">
                Create a work
              </Link>
            }
          />
        )
      ) : null}

      {items.length > 0 ? (
        <ul className="work-grid">
          {items.map((work) => (
            <li key={work.id}>
              <WorkCard work={work} to={`/member/works/${work.id}/edit`} />
            </li>
          ))}
        </ul>
      ) : null}

      {items.length > 0 ? (
        <Pagination page={data?.page ?? 1} pages={data?.pages ?? 1} total={data?.total ?? 0} onChange={setPage} />
      ) : null}
    </div>
  )
}
