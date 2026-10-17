/**
 * Admin clients — paginated list with ordering, featured filter and a
 * client-side search within the loaded page (the backend exposes no text
 * search), plus edit and delete.
 */

import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { useAdminClients } from '../../features/clients/hooks'
import { deleteClient } from '../../features/clients/api'
import { useAuth } from '../../app/providers/AuthProvider'
import { canDelete } from '../../features/auth/rbac'
import { PageHeader } from '../../components/admin/PageHeader'
import { Pagination } from '../../components/admin/Pagination'
import { TextInput } from '../../components/form/TextInput'
import { Checkbox } from '../../components/form/Checkbox'
import { ConfirmDialog } from '../../components/form/ConfirmDialog'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { EmptyState } from '../../components/ui/EmptyState'
import type { AdminClient } from '../../types'

export default function AdminClientsPage() {
  usePageMeta({ title: 'Clients — Admin — Thridha Labs' })

  const { user } = useAuth()
  const mayDelete = canDelete(user?.role)

  const [page, setPage] = useState(1)
  const [featuredOnly, setFeaturedOnly] = useState(false)
  const [query, setQuery] = useState('')

  const { data, loading, error, reload } = useAdminClients({
    page,
    page_size: 20,
    sort: 'display_order',
    order: 'asc',
    featured: featuredOnly || undefined,
  })
  useAdminSessionIssue(error)

  const [pendingDelete, setPendingDelete] = useState<AdminClient | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const rows = useMemo(() => {
    const items = data?.items ?? []
    const needle = query.trim().toLowerCase()
    if (!needle) return items
    return items.filter(
      (client) =>
        client.name.toLowerCase().includes(needle) ||
        client.slug.toLowerCase().includes(needle) ||
        (client.industry ?? '').toLowerCase().includes(needle),
    )
  }, [data, query])

  async function handleDelete(): Promise<void> {
    if (!pendingDelete) return
    setDeleting(true)
    setActionError(null)
    try {
      await deleteClient(pendingDelete.id)
      setPendingDelete(null)
      await reload()
    } catch (caught) {
      setActionError(getErrorMessage(caught, 'Could not delete the client.'))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Content"
        title="Clients"
        description="People and companies you work with."
        actionLabel="Add client"
        actionTo="/admin/clients/new"
      />

      <div className="admin-toolbar">
        <TextInput
          id="clients-search"
          aria-label="Search clients"
          placeholder="Search loaded clients…"
          value={query}
          onChange={setQuery}
          className="admin-toolbar__search"
        />
        <Checkbox
          id="clients-featured"
          label="Featured only"
          checked={featuredOnly}
          onChange={setFeaturedOnly}
        />
      </div>

      {loading ? <ContentSkeleton rows={4} /> : null}
      {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}
      {!loading && !error && rows.length === 0 ? (
        query || featuredOnly ? (
          <EmptyState title="No matches" description="Try a different search or clear the filter." />
        ) : (
          <EmptyState title="No clients yet" description="Add your first client to get started." />
        )
      ) : null}

      {rows.length > 0 ? (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Featured</th>
                <th>Projects</th>
                <th className="admin-table__num">Order</th>
                <th className="admin-table__actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((client) => (
                <tr key={client.id}>
                  <td>
                    <Link to={`/admin/clients/${client.id}`} className="admin-table__name">
                      {client.name}
                    </Link>
                    <span className="admin-table__sub mono">/{client.slug}</span>
                  </td>
                  <td>{client.featured ? <span className="chip chip--ok">Featured</span> : <span className="chip">—</span>}</td>
                  <td>{client.project_ids.length}</td>
                  <td className="admin-table__num">{client.display_order}</td>
                  <td className="admin-table__actions">
                    <Link className="btn btn--ghost btn--sm" to={`/admin/clients/${client.id}`}>
                      Edit
                    </Link>
                    {mayDelete ? (
                      <button type="button" className="btn btn--ghost btn--sm" onClick={() => setPendingDelete(client)}>
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
        title="Delete this client?"
        body={
          pendingDelete
            ? `"${pendingDelete.name}" will be permanently removed. The backend blocks deletion while it is referenced by projects.`
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