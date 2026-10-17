/**
 * Admin progress reports — the review queue. Lists member progress reports
 * with a status filter (defaults to those awaiting review) and author/project
 * search, and links into the review detail where decisions are recorded.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAdminReports } from '../../features/reports/hooks'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { usePageMeta } from '../../lib/utils/seo'
import { ReportStatusChip } from '../../components/reports/ReportStatusChip'
import { PageHeader } from '../../components/admin/PageHeader'
import { Pagination } from '../../components/admin/Pagination'
import { TextInput } from '../../components/form/TextInput'
import { Select } from '../../components/form/Select'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { EmptyState } from '../../components/ui/EmptyState'
import type { ReportStatus } from '../../types/report'

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'pending', label: 'Awaiting review' },
  { value: 'changes_requested', label: 'Changes requested' },
  { value: 'approved', label: 'Approved' },
]

function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString()
}

function snippet(text: string, max = 110): string {
  return text.length > max ? `${text.slice(0, max).trimEnd()}…` : text
}

export default function AdminReportsPage() {
  usePageMeta({ title: 'Progress reports — Admin — Thridha Labs' })

  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<'' | ReportStatus>('pending')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')

  const { data, loading, error, reload } = useAdminReports({
    page,
    page_size: 20,
    status: status || undefined,
    search: search || undefined,
  })
  useAdminSessionIssue(error)

  const items = data?.items ?? []

  function handleSearchSubmit(event: React.FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    setPage(1)
    setSearch(searchInput.trim())
  }

  const isFiltering = status !== '' || search.trim() !== ''

  return (
    <div>
      <PageHeader
        eyebrow="Review"
        title="Progress reports"
        description="Short member-authored updates on projects, awaiting your review."
      />

      <form className="admin-toolbar" onSubmit={handleSearchSubmit}>
        <TextInput
          id="reports-search"
          aria-label="Search reports"
          placeholder="Search member or project…"
          value={searchInput}
          onChange={setSearchInput}
          className="admin-toolbar__search"
        />
        <button type="submit" className="btn btn--ghost btn--sm">
          Search
        </button>
        <Select
          id="reports-review-status"
          aria-label="Filter by status"
          options={STATUS_OPTIONS}
          value={status}
          onChange={(value) => {
            setStatus(value as '' | ReportStatus)
            setPage(1)
          }}
        />
      </form>

      {loading ? <ContentSkeleton rows={5} /> : null}
      {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}

      {!loading && !error && items.length === 0 ? (
        isFiltering ? (
          <EmptyState title="No matches" description="No reports match that filter." />
        ) : (
          <EmptyState
            title="Nothing to review"
            description="Progress reports awaiting review will appear here."
          />
        )
      ) : null}

      {items.length > 0 ? (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Report</th>
                <th>Member</th>
                <th>Project</th>
                <th>Status</th>
                <th>Submitted</th>
                <th className="admin-table__actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((report) => (
                <tr key={report.id}>
                  <td>
                    <Link className="admin-table__name" to={`/admin/reports/${report.id}`}>
                      {report.activity_title}
                    </Link>
                    <span className="admin-table__sub">{snippet(report.description)}</span>
                  </td>
                  <td>
                    {report.member_name}
                    <span className="admin-table__sub mono">{report.member_readable_id}</span>
                  </td>
                  <td>
                    {report.role ? report.role : <span className="admin-table__muted">—</span>}
                  </td>
                  <td>
                    <ReportStatusChip status={report.status} />
                  </td>
                  <td>{formatDate(report.submitted_at)}</td>
                  <td className="admin-table__actions">
                    <Link className="btn btn--ghost btn--sm" to={`/admin/reports/${report.id}`}>
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
        <Pagination
          page={data?.page ?? 1}
          pages={data?.pages ?? 1}
          total={data?.total ?? 0}
          onChange={setPage}
        />
      ) : null}
    </div>
  )
}
