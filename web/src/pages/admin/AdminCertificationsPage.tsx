/**
 * Admin certifications — the review queue. Lists certification requests with a
 * status filter and links into the review detail (frozen snapshot).
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAdminCertifications } from '../../features/certifications/hooks'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { usePageMeta } from '../../lib/utils/seo'
import { CERTIFICATION_STATUS_LABELS } from '../../features/certifications/status'
import { CertificationStatusChip } from '../../components/certifications/CertificationStatusChip'
import { PageHeader } from '../../components/admin/PageHeader'
import { Pagination } from '../../components/admin/Pagination'
import { Select } from '../../components/form/Select'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { EmptyState } from '../../components/ui/EmptyState'
import type { CertificationStatus } from '../../types/certification'

function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString()
}

export default function AdminCertificationsPage() {
  usePageMeta({ title: 'Certifications — Admin — Thridha Labs' })

  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<'' | CertificationStatus>('')

  const { data, loading, error, reload } = useAdminCertifications({
    page,
    page_size: 20,
    status: status || undefined,
  })
  useAdminSessionIssue(error)

  const items = data?.items ?? []

  return (
    <div>
      <PageHeader
        eyebrow="Review"
        title="Certifications"
        description="Works submitted by members for certification review."
      />

      <div className="admin-toolbar">
        <Select
          id="certifications-status"
          aria-label="Filter by status"
          placeholder="All statuses"
          options={Object.entries(CERTIFICATION_STATUS_LABELS).map(([value, label]) => ({ value, label }))}
          value={status}
          onChange={(value) => {
            setStatus(value as '' | CertificationStatus)
            setPage(1)
          }}
        />
      </div>

      {loading ? <ContentSkeleton rows={5} /> : null}
      {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}

      {!loading && !error && items.length === 0 ? (
        status ? (
          <EmptyState title="No matches" description="No certification requests with that status." />
        ) : (
          <EmptyState title="No certification requests" description="Requests will appear here as members submit them." />
        )
      ) : null}

      {items.length > 0 ? (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Work</th>
                <th>Member</th>
                <th>Status</th>
                <th>Submitted</th>
                <th className="admin-table__num">Snapshot</th>
                <th className="admin-table__actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((request) => (
                <tr key={request.id}>
                  <td>
                    <Link className="admin-table__name" to={`/admin/certifications/${request.id}`}>
                      {request.work.title}
                    </Link>
                    {request.changed_since_review ? (
                      <span className="chip chip--warn" style={{ marginLeft: 'var(--space-2)' }}>
                        Changed since review
                      </span>
                    ) : null}
                  </td>
                  <td>
                    {request.member.name}
                    <span className="admin-table__sub mono">{request.member.member_id}</span>
                  </td>
                  <td>
                    <CertificationStatusChip status={request.status} />
                  </td>
                  <td>{formatDate(request.submitted_at)}</td>
                  <td className="admin-table__num">v{request.snapshot_version}</td>
                  <td className="admin-table__actions">
                    <Link className="btn btn--ghost btn--sm" to={`/admin/certifications/${request.id}`}>
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
