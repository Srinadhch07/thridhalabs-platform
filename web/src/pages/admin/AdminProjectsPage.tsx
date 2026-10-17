/**
 * Admin projects — paginated list with status / type / featured filters,
 * client-side search within the loaded page, editing and deletion.
 */

import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { useAdminProjects } from '../../features/projects/hooks'
import { deleteProject } from '../../features/projects/api'
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
import type { AdminProject, ProjectStatus, ProjectType } from '../../types'

const STATUS_LABELS: Record<ProjectStatus, string> = {
  draft: 'Draft',
  published: 'Published',
  archived: 'Archived',
}

const TYPE_LABELS: Record<ProjectType, string> = {
  'client-work': 'Client work',
  product: 'Product',
  experiment: 'Experiment',
  'member-contribution': 'Member contribution',
}

export default function AdminProjectsPage() {
  usePageMeta({ title: 'Projects — Admin — Thridha Labs' })

  const { user } = useAuth()
  const mayDelete = canDelete(user?.role)

  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<'' | ProjectStatus>('')
  const [projectType, setProjectType] = useState<'' | ProjectType>('')
  const [featuredOnly, setFeaturedOnly] = useState(false)
  const [query, setQuery] = useState('')

  const { data, loading, error, reload } = useAdminProjects({
    page,
    page_size: 20,
    sort: 'display_order',
    order: 'asc',
    status: status || undefined,
    project_type: projectType || undefined,
    featured: featuredOnly || undefined,
  })
  useAdminSessionIssue(error)

  const [pendingDelete, setPendingDelete] = useState<AdminProject | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const rows = useMemo(() => {
    const items = data?.items ?? []
    const needle = query.trim().toLowerCase()
    if (!needle) return items
    return items.filter(
      (project) =>
        project.name.toLowerCase().includes(needle) ||
        project.slug.toLowerCase().includes(needle) ||
        (project.category ?? '').toLowerCase().includes(needle) ||
        project.technologies.some((tech) => tech.toLowerCase().includes(needle)),
    )
  }, [data, query])

  async function handleDelete(): Promise<void> {
    if (!pendingDelete) return
    setDeleting(true)
    setActionError(null)
    try {
      await deleteProject(pendingDelete.id)
      setPendingDelete(null)
      await reload()
    } catch (caught) {
      setActionError(getErrorMessage(caught, 'Could not delete the project.'))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Content"
        title="Projects"
        description="Work, products and experiments."
        actionLabel="Add project"
        actionTo="/admin/projects/new"
      />

      <div className="admin-toolbar">
        <TextInput
          id="projects-search"
          aria-label="Search projects"
          placeholder="Search loaded projects…"
          value={query}
          onChange={setQuery}
          className="admin-toolbar__search"
        />
        <Select
          id="projects-status"
          aria-label="Filter by status"
          placeholder="All statuses"
          options={Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label }))}
          value={status}
          onChange={(value) => setStatus(value as '' | ProjectStatus)}
        />
        <Select
          id="projects-type"
          aria-label="Filter by type"
          placeholder="All types"
          options={Object.entries(TYPE_LABELS).map(([value, label]) => ({ value, label }))}
          value={projectType}
          onChange={(value) => setProjectType(value as '' | ProjectType)}
        />
        <Checkbox
          id="projects-featured"
          label="Featured only"
          checked={featuredOnly}
          onChange={setFeaturedOnly}
        />
      </div>

      {loading ? <ContentSkeleton rows={4} /> : null}
      {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}
      {!loading && !error && rows.length === 0 ? (
        query || status || projectType || featuredOnly ? (
          <EmptyState title="No matches" description="Try a different filter or search." />
        ) : (
          <EmptyState title="No projects yet" description="Add your first project to get started." />
        )
      ) : null}

      {rows.length > 0 ? (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Project</th>
                <th>Status</th>
                <th>Type</th>
                <th>Client</th>
                <th>Featured</th>
                <th className="admin-table__num">Order</th>
                <th className="admin-table__actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((project) => (
                <tr key={project.id}>
                  <td>
                    <Link to={`/admin/projects/${project.id}`} className="admin-table__name">
                      {project.name}
                    </Link>
                    <span className="admin-table__sub mono">/{project.slug}</span>
                  </td>
                  <td>
                    <span className={`chip chip--${project.status}`}>{STATUS_LABELS[project.status]}</span>
                  </td>
                  <td>{TYPE_LABELS[project.project_type]}</td>
                  <td>{project.client?.name ?? <span className="admin-table__muted">—</span>}</td>
                  <td>{project.featured ? <span className="chip chip--ok">Featured</span> : <span className="chip">—</span>}</td>
                  <td className="admin-table__num">{project.display_order}</td>
                  <td className="admin-table__actions">
                    <Link className="btn btn--ghost btn--sm" to={`/admin/projects/${project.id}`}>
                      Edit
                    </Link>
                    {project.status === 'published' ? (
                      <Link className="btn btn--ghost btn--sm" to={`/projects/${project.slug}`}>
                        View
                      </Link>
                    ) : null}
                    {mayDelete ? (
                      <button type="button" className="btn btn--ghost btn--sm" onClick={() => setPendingDelete(project)}>
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
        title="Delete this project?"
        body={pendingDelete ? `"${pendingDelete.name}" will be permanently removed.` : ''}
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