/**
 * Admin careers opportunities — paginated list with status / type filters,
 * client-side search within the loaded page, editing and deletion.
 */

import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { useAdminOpportunities } from '../../features/careers/hooks'
import { deleteOpportunity } from '../../features/careers/api'
import { useAuth } from '../../app/providers/AuthProvider'
import { canDelete } from '../../features/auth/rbac'
import { PageHeader } from '../../components/admin/PageHeader'
import { Pagination } from '../../components/admin/Pagination'
import { TextInput } from '../../components/form/TextInput'
import { Select } from '../../components/form/Select'
import { ConfirmDialog } from '../../components/form/ConfirmDialog'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { EmptyState } from '../../components/ui/EmptyState'
import type { OpportunityStatus, OpportunityType } from '../../types'

const STATUS_LABELS: Record<OpportunityStatus, string> = {
  draft: 'Draft',
  open: 'Open',
  closed: 'Closed',
}

const TYPE_LABELS: Record<OpportunityType, string> = {
  'lab-member': 'Lab Member',
  internship: 'Internship',
  'full-time': 'Full-time',
  'part-time': 'Part-time',
  contract: 'Contract',
  other: 'Other',
}

export default function AdminCareersOpportunitiesPage() {
  usePageMeta({ title: 'Opportunities — Admin — Thridha Labs' })

  const { user } = useAuth()
  const mayDelete = canDelete(user?.role)

  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<'' | OpportunityStatus>('')
  const [opportunityType, setOpportunityType] = useState<'' | OpportunityType>('')
  const [query, setQuery] = useState('')

  const { data, loading, error, reload } = useAdminOpportunities({
    page,
    page_size: 20,
    sort: 'display_order',
    order: 'asc',
    status: status || undefined,
    type: opportunityType || undefined,
  })
  useAdminSessionIssue(error)

  const [pendingDelete, setPendingDelete] = useState<{ id: string; title: string } | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const rows = useMemo(() => {
    const items = data?.items ?? []
    const needle = query.trim().toLowerCase()
    if (!needle) return items
    return items.filter(
      (opportunity) =>
        opportunity.title.toLowerCase().includes(needle) ||
        opportunity.slug.toLowerCase().includes(needle) ||
        opportunity.skills.some((skill) => skill.toLowerCase().includes(needle)),
    )
  }, [data, query])

  async function handleDelete(): Promise<void> {
    if (!pendingDelete) return
    setDeleting(true)
    setActionError(null)
    try {
      await deleteOpportunity(pendingDelete.id)
      setPendingDelete(null)
      await reload()
    } catch (caught) {
      setActionError(getErrorMessage(caught, 'Could not delete the opportunity.'))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Content"
        title="Opportunities"
        description="Roles open to the lab."
        actionLabel="Add opportunity"
        actionTo="/admin/careers/opportunities/new"
      />

      <div className="admin-toolbar">
        <TextInput
          id="opportunities-search"
          aria-label="Search opportunities"
          placeholder="Search loaded opportunities…"
          value={query}
          onChange={setQuery}
          className="admin-toolbar__search"
        />
        <Select
          id="opportunities-status"
          aria-label="Filter by status"
          placeholder="All statuses"
          options={Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label }))}
          value={status}
          onChange={(value) => setStatus(value as '' | OpportunityStatus)}
        />
        <Select
          id="opportunities-type"
          aria-label="Filter by type"
          placeholder="All types"
          options={Object.entries(TYPE_LABELS).map(([value, label]) => ({ value, label }))}
          value={opportunityType}
          onChange={(value) => setOpportunityType(value as '' | OpportunityType)}
        />
      </div>

      {loading ? <ContentSkeleton rows={4} /> : null}
      {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}
      {!loading && !error && rows.length === 0 ? (
        query || status || opportunityType ? (
          <EmptyState title="No matches" description="Try a different filter or search." />
        ) : (
          <EmptyState title="No opportunities yet" description="Add your first opportunity to get started." />
        )
      ) : null}

      {rows.length > 0 ? (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Role</th>
                <th>Status</th>
                <th>Type</th>
                <th>Work mode</th>
                <th className="admin-table__num">Order</th>
                <th className="admin-table__actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((opportunity) => (
                <tr key={opportunity.id}>
                  <td>
                    <Link to={`/admin/careers/opportunities/${opportunity.id}`} className="admin-table__name">
                      {opportunity.title}
                    </Link>
                    <span className="admin-table__sub mono">/{opportunity.slug}</span>
                  </td>
                  <td>
                    <span className={`chip chip--${opportunity.status}`}>{STATUS_LABELS[opportunity.status]}</span>
                  </td>
                  <td>
                    {opportunity.type === 'other' && opportunity.custom_type
                      ? opportunity.custom_type
                      : TYPE_LABELS[opportunity.type]}
                  </td>
                  <td>{opportunity.work_mode ? opportunity.work_mode : <span className="admin-table__muted">—</span>}</td>
                  <td className="admin-table__num">{opportunity.display_order}</td>
                  <td className="admin-table__actions">
                    <Link className="btn btn--ghost btn--sm" to={`/admin/careers/opportunities/${opportunity.id}`}>
                      Edit
                    </Link>
                    {opportunity.status === 'open' ? (
                      <Link className="btn btn--ghost btn--sm" to={`/careers`} target="_blank" rel="noreferrer">
                        View
                      </Link>
                    ) : null}
                    {mayDelete ? (
                      <button type="button" className="btn btn--ghost btn--sm" onClick={() => setPendingDelete(opportunity)}>
                        Delete
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {rows.length > 0 ? (
        <Pagination page={data?.page ?? 1} pages={data?.pages ?? 1} total={data?.total ?? 0} onChange={setPage} />
      ) : null}

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete this opportunity?"
        body={pendingDelete ? `"${pendingDelete.title}" will be permanently removed.` : ''}
        confirmLabel="Delete"
        cancelLabel="Cancel"
        danger
        busy={deleting}
        onConfirm={() => void handleDelete()}
        onCancel={() => {
          if (!deleting) setPendingDelete(null)
        }}
      />
      {actionError ? (
        <p className="form-field__error form-field__error--form" role="alert">
          {actionError}
        </p>
      ) : null}
    </div>
  )
}