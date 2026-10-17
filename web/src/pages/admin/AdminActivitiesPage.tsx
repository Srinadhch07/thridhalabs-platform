/**
 * Admin activities — paginated list with status / type / featured filters,
 * client-side search, lifecycle status and deletion.
 */

import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAdminActivities } from '../../features/activities/hooks'
import { deleteAdminActivity } from '../../features/activities/api'
import {
  ACTIVITY_STATUS_LABELS,
  ACTIVITY_TYPE_LABELS,
  PRESENTATION_LABELS,
} from '../../features/activities/labels'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { useAuth } from '../../app/providers/AuthProvider'
import { canDelete } from '../../features/auth/rbac'
import { PageHeader } from '../../components/admin/PageHeader'
import { Pagination } from '../../components/admin/Pagination'
import { TextInput } from '../../components/form/TextInput'
import { Select } from '../../components/form/Select'
import { Checkbox } from '../../components/form/Checkbox'
import { ConfirmDialog } from '../../components/form/ConfirmDialog'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { EmptyState } from '../../components/ui/EmptyState'
import type { ActivityStatus, ActivityType, AdminActivity } from '../../types/activity'

export default function AdminActivitiesPage() {
  usePageMeta({ title: 'Activities — Admin — Thridha Labs' })

  const { user } = useAuth()
  const mayDelete = canDelete(user?.role)

  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<'' | ActivityStatus>('')
  const [activityType, setActivityType] = useState<'' | ActivityType>('')
  const [featuredOnly, setFeaturedOnly] = useState(false)
  const [query, setQuery] = useState('')

  const { data, loading, error, reload } = useAdminActivities({
    page,
    page_size: 20,
    sort: 'display_order',
    order: 'asc',
    status: status || undefined,
    activity_type: activityType || undefined,
    featured: featuredOnly || undefined,
  })
  useAdminSessionIssue(error)

  const [pendingDelete, setPendingDelete] = useState<AdminActivity | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const rows = useMemo(() => {
    const items = data?.items ?? []
    const needle = query.trim().toLowerCase()
    if (!needle) return items
    return items.filter(
      (activity) =>
        activity.title.toLowerCase().includes(needle) ||
        activity.slug.toLowerCase().includes(needle) ||
        activity.tags.some((tag) => tag.toLowerCase().includes(needle)),
    )
  }, [data, query])

  async function handleDelete(): Promise<void> {
    if (!pendingDelete) return
    setDeleting(true)
    setActionError(null)
    try {
      await deleteAdminActivity(pendingDelete.id)
      setPendingDelete(null)
      await reload()
    } catch (caught) {
      setActionError(getErrorMessage(caught, 'Could not delete the activity.'))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Programmes"
        title="Activities"
        description="Projects, programmes and hackathons."
        actionLabel="Add activity"
        actionTo="/admin/activities/new"
      />

      <div className="admin-toolbar">
        <TextInput
          id="activities-search"
          aria-label="Search activities"
          placeholder="Search loaded activities…"
          value={query}
          onChange={setQuery}
          className="admin-toolbar__search"
        />
        <Select
          id="activities-status"
          aria-label="Filter by status"
          placeholder="All statuses"
          options={Object.entries(ACTIVITY_STATUS_LABELS).map(([value, label]) => ({ value, label }))}
          value={status}
          onChange={(value) => {
            setStatus(value as '' | ActivityStatus)
            setPage(1)
          }}
        />
        <Select
          id="activities-type"
          aria-label="Filter by type"
          placeholder="All types"
          options={Object.entries(ACTIVITY_TYPE_LABELS).map(([value, label]) => ({ value, label }))}
          value={activityType}
          onChange={(value) => {
            setActivityType(value as '' | ActivityType)
            setPage(1)
          }}
        />
        <Checkbox
          id="activities-featured"
          label="Featured only"
          checked={featuredOnly}
          onChange={(value) => {
            setFeaturedOnly(value)
            setPage(1)
          }}
        />
      </div>

      {loading ? <ContentSkeleton rows={4} /> : null}
      {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}
      {!loading && !error && rows.length === 0 ? (
        query || status || activityType || featuredOnly ? (
          <EmptyState title="No matches" description="Try a different filter or search." />
        ) : (
          <EmptyState title="No activities yet" description="Add your first activity to get started." />
        )
      ) : null}

      {rows.length > 0 ? (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Activity</th>
                <th>Status</th>
                <th>Type</th>
                <th>Presentation</th>
                <th>Participants</th>
                <th className="admin-table__num">Order</th>
                <th className="admin-table__actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((activity) => (
                <tr key={activity.id}>
                  <td>
                    <Link to={`/admin/activities/${activity.id}`} className="admin-table__name">
                      {activity.title}
                    </Link>
                    <span className="admin-table__sub mono">/{activity.slug}</span>
                  </td>
                  <td>
                    <span className={`chip chip--${activity.status}`}>
                      {ACTIVITY_STATUS_LABELS[activity.status]}
                    </span>
                  </td>
                  <td>{ACTIVITY_TYPE_LABELS[activity.activity_type]}</td>
                  <td>{PRESENTATION_LABELS[activity.presentation_status]}</td>
                  <td className="admin-table__num">
                    {Object.values(activity.participant_counts).reduce((sum, n) => sum + n, 0)}
                  </td>
                  <td className="admin-table__num">{activity.display_order}</td>
                  <td className="admin-table__actions">
                    <Link className="btn btn--ghost btn--sm" to={`/admin/activities/${activity.id}`}>
                      Edit
                    </Link>
                    {activity.status === 'published' ? (
                      <Link className="btn btn--ghost btn--sm" to={`/activities/${activity.slug}`}>
                        View
                      </Link>
                    ) : null}
                    {mayDelete ? (
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        onClick={() => setPendingDelete(activity)}
                      >
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
        title="Delete this activity?"
        body={
          pendingDelete
            ? `"${pendingDelete.title}" and all its participation records will be permanently removed.`
            : ''
        }
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
