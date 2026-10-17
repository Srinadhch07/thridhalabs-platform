/**
 * Admin testimonials — paginated list with publish/featured filters, editing
 * and deletion. Includes an explanatory legend for where each testimonial
 * appears on the public site.
 */

import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { useAdminTestimonials } from '../../features/testimonials/hooks'
import { deleteTestimonial, updateTestimonial } from '../../features/testimonials/api'
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
import type { AdminTestimonial, TestimonialStatus } from '../../types'

const STATUS_LABELS: Record<TestimonialStatus, string> = {
  pending: 'Pending',
  approved: 'Approved',
  rejected: 'Rejected',
}

export default function AdminTestimonialsPage() {
  usePageMeta({ title: 'Testimonials — Admin — Thridha Labs' })

  const { user } = useAuth()
  const mayDelete = canDelete(user?.role)

  const [page, setPage] = useState(1)
  const [published, setPublished] = useState<'' | 'published' | 'unpublished'>('')
  const [status, setStatus] = useState<'' | TestimonialStatus>('')
  const [featuredOnly, setFeaturedOnly] = useState(false)
  const [query, setQuery] = useState('')

  const { data, loading, error, reload } = useAdminTestimonials({
    page,
    page_size: 20,
    sort: 'display_order',
    order: 'asc',
    published:
      published === '' ? undefined : published === 'published' ? true : false,
    status: status || undefined,
    featured: featuredOnly || undefined,
  })
  useAdminSessionIssue(error)

  const [pendingDelete, setPendingDelete] = useState<AdminTestimonial | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [moderatingId, setModeratingId] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const rows = useMemo(() => {
    const items = data?.items ?? []
    const needle = query.trim().toLowerCase()
    if (!needle) return items
    return items.filter(
      (item) =>
        item.person_name.toLowerCase().includes(needle) ||
        (item.company ?? '').toLowerCase().includes(needle) ||
        item.testimonial_text.toLowerCase().includes(needle),
    )
  }, [data, query])

  async function handleModerate(item: AdminTestimonial, next: TestimonialStatus): Promise<void> {
    setModeratingId(item.id)
    setActionError(null)
    try {
      await updateTestimonial(item.id, { status: next })
      await reload()
    } catch (caught) {
      setActionError(getErrorMessage(caught, 'Could not update the testimonial.'))
    } finally {
      setModeratingId(null)
    }
  }

  async function handleDelete(): Promise<void> {
    if (!pendingDelete) return
    setDeleting(true)
    setActionError(null)
    try {
      await deleteTestimonial(pendingDelete.id)
      setPendingDelete(null)
      await reload()
    } catch (caught) {
      setActionError(getErrorMessage(caught, 'Could not delete the testimonial.'))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Content"
        title="Testimonials"
        description="What people say about the lab."
        actionLabel="Add testimonial"
        actionTo="/admin/testimonials/new"
      />

      <p className="behavior-note">
        <strong>Where it shows:</strong> approved + featured → home page · approved → testimonials page ·
        pending or rejected → nowhere. Approving also publishes; rejecting unpublishes.
      </p>

      <div className="admin-toolbar">
        <TextInput
          id="testimonials-search"
          aria-label="Search testimonials"
          placeholder="Search loaded testimonials…"
          value={query}
          onChange={setQuery}
          className="admin-toolbar__search"
        />
        <Select
          id="testimonials-published"
          aria-label="Filter by publication"
          placeholder="All publication states"
          options={[
            { value: 'published', label: 'Published' },
            { value: 'unpublished', label: 'Unpublished' },
          ]}
          value={published}
          onChange={(value) => setPublished(value as '' | 'published' | 'unpublished')}
        />
        <Select
          id="testimonials-status"
          aria-label="Filter by moderation status"
          placeholder="All statuses"
          options={(Object.keys(STATUS_LABELS) as TestimonialStatus[]).map((value) => ({
            value,
            label: STATUS_LABELS[value],
          }))}
          value={status}
          onChange={(value) => setStatus(value as '' | TestimonialStatus)}
        />
        <Checkbox
          id="testimonials-featured"
          label="Featured only"
          checked={featuredOnly}
          onChange={setFeaturedOnly}
        />
      </div>

      {loading ? <ContentSkeleton rows={4} /> : null}
      {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}
      {!loading && !error && rows.length === 0 ? (
        query || published || status || featuredOnly ? (
          <EmptyState title="No matches" description="Try a different filter or search." />
        ) : (
          <EmptyState title="No testimonials yet" description="Add your first testimonial to get started." />
        )
      ) : null}

      {rows.length > 0 ? (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Person</th>
                <th>Status</th>
                <th>Featured</th>
                <th>Rating</th>
                <th className="admin-table__num">Order</th>
                <th className="admin-table__actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((item) => (
                <tr key={item.id}>
                  <td>
                    <Link to={`/admin/testimonials/${item.id}`} className="admin-table__name">
                      {item.person_name}
                    </Link>
                    <span className="admin-table__sub">
                      {item.role} {item.company ? `· ${item.company}` : ''}
                    </span>
                  </td>
                  <td>
                    <span className={`chip ${item.published ? 'chip--ok' : 'chip--muted'}`}>
                      {item.published ? 'Published' : 'Unpublished'}
                    </span>{' '}
                    <span
                      className={`chip ${
                        item.status === 'approved'
                          ? 'chip--ok'
                          : item.status === 'pending'
                            ? 'chip--warn'
                            : 'chip--muted'
                      }`}
                    >
                      {STATUS_LABELS[item.status] ?? item.status}
                    </span>
                  </td>
                  <td>{item.featured ? <span className="chip chip--ok">Featured</span> : <span className="chip">—</span>}</td>
                  <td>{'★'.repeat(item.rating)}</td>
                  <td className="admin-table__num">{item.display_order}</td>
                  <td className="admin-table__actions">
                    {item.status !== 'approved' ? (
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        disabled={moderatingId === item.id}
                        onClick={() => void handleModerate(item, 'approved')}
                      >
                        Approve
                      </button>
                    ) : null}
                    {item.status !== 'rejected' ? (
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        disabled={moderatingId === item.id}
                        onClick={() => void handleModerate(item, 'rejected')}
                      >
                        Reject
                      </button>
                    ) : null}
                    <Link className="btn btn--ghost btn--sm" to={`/admin/testimonials/${item.id}`}>
                      Edit
                    </Link>
                    {mayDelete ? (
                      <button type="button" className="btn btn--ghost btn--sm" onClick={() => setPendingDelete(item)}>
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
        title="Delete this testimonial?"
        body={pendingDelete ? `The testimonial by ${pendingDelete.person_name} will be permanently removed.` : ''}
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