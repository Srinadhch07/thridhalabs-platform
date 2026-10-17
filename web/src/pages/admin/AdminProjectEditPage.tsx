/**
 * Admin project editor — create (`/admin/projects/new`) and edit
 * (`/admin/projects/:id`).
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { useBeforeUnload } from '../../lib/hooks/useBeforeUnload'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { useAdminProject } from '../../features/projects/hooks'
import { useAdminClients } from '../../features/clients/hooks'
import { createProject, updateProject } from '../../features/projects/api'
import { resolveAdminMediaPreviewUrl, uploadMedia } from '../../features/media/api'
import { PageHeader } from '../../components/admin/PageHeader'
import { FormField } from '../../components/form/FormField'
import { TextInput } from '../../components/form/TextInput'
import { Textarea } from '../../components/form/Textarea'
import { Select } from '../../components/form/Select'
import { Checkbox } from '../../components/form/Checkbox'
import { ImageUploadField, ImageGalleryField } from '../../components/form/ImageUploadField'
import { FormActions } from '../../components/form/FormActions'
import { SaveButton } from '../../components/form/SaveButton'
import { ConfirmDialog } from '../../components/form/ConfirmDialog'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import type { ProjectStatus, ProjectType } from '../../types'

export default function AdminProjectEditPage() {
  const { projectId = 'new' } = useParams()
  const isNew = projectId === 'new'
  usePageMeta({ title: `${isNew ? 'New project' : 'Edit project'} — Admin — Thridha Labs` })

  const navigate = useNavigate()
  const { data, loading, error, reload } = useAdminProject(isNew ? undefined : projectId)
  useAdminSessionIssue(error)

  const clients = useAdminClients({ page: 1, page_size: 100, sort: 'name', order: 'asc' })
  useAdminSessionIssue(clients.error)

  const [form, setForm] = useState({
    name: '',
    slug: '',
    status: 'draft' as ProjectStatus,
    project_type: '' as '' | ProjectType,
    category: '',
    client_id: '',
    description: '',
    technologies: '',
    live_url: '',
    github_url: '',
    completion_date: '',
    featured: false,
    display_order: '0',
    thumbnail_media_id: null as string | null,
    gallery: [] as string[],
  })

  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [discardOpen, setDiscardOpen] = useState(false)

  useBeforeUnload(dirty)

  const hydrated = useRef(false)
  useEffect(() => {
    if (!data || hydrated.current) return
    hydrated.current = true
    setForm({
      name: data.name,
      slug: data.slug,
      status: data.status,
      project_type: data.project_type,
      category: data.category ?? '',
      client_id: data.client_id ?? '',
      description: data.description ?? '',
      technologies: data.technologies.join(', '),
      live_url: data.live_url ?? '',
      github_url: data.github_url ?? '',
      completion_date: data.completion_date ?? '',
      featured: data.featured,
      display_order: String(data.display_order),
      thumbnail_media_id: data.thumbnail_media_id,
      gallery: data.gallery_media_ids,
    })
    setDirty(false)
  }, [data])

  function patch(p: Partial<typeof form>): void {
    setForm((prev) => ({ ...prev, ...p }))
    setDirty(true)
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    if (!form.name.trim()) {
      setSaveError('Project name is required.')
      return
    }
    if (!form.project_type) {
      setSaveError('Choose a project type.')
      return
    }
    const payload = {
      name: form.name.trim(),
      slug: form.slug.trim() || null,
      status: form.status,
      project_type: form.project_type,
      category: form.category.trim() || null,
      client_id: form.client_id || null,
      description: form.description,
      technologies: form.technologies
        .split(',')
        .map((tech) => tech.trim())
        .filter(Boolean),
      live_url: form.live_url.trim() || null,
      github_url: form.github_url.trim() || null,
      completion_date: form.completion_date || null,
      featured: form.featured,
      display_order: Number(form.display_order || 0),
      thumbnail_media_id: form.thumbnail_media_id,
      gallery_media_ids: form.gallery,
    }
    setSaving(true)
    setSaveError(null)
    try {
      if (isNew) {
        await createProject(payload)
      } else {
        await updateProject(projectId, payload)
      }
      setDirty(false)
      navigate('/admin/projects')
    } catch (caught) {
      setSaveError(getErrorMessage(caught, 'Could not save the project.'))
    } finally {
      setSaving(false)
    }
  }

  function handleCancel(): void {
    if (dirty) {
      setDiscardOpen(true)
    } else {
      navigate('/admin/projects')
    }
  }

  const clientOptions = useMemo(
    () =>
      (clients.data?.items ?? []).map((client) => ({
        value: client.id,
        label: client.name,
      })),
    [clients.data],
  )

  const previewable = !isNew && data?.status === 'published' && data.slug

  if (!isNew && loading) {
    return <ContentSkeleton rows={6} />
  }

  if (!isNew && error) {
    return <ErrorState error={error} onRetry={reload} />
  }

  return (
    <div>
      <PageHeader
        eyebrow="Content"
        title={isNew ? 'Add project' : 'Edit project'}
        description={isNew ? 'Create a new project, product or experiment.' : 'Update project details.'}
      />

      <form className="admin-form" onSubmit={handleSubmit} noValidate>
        <section className="admin-section">
          <h2 className="admin-section__title">Basics</h2>
          <FormField id="project-name" label="Project name" required>
            <TextInput
              id="project-name"
              value={form.name}
              onChange={(value) => patch({ name: value })}
              placeholder="Atlas Engine"
            />
          </FormField>
          <FormField id="project-slug" label="Slug" hint="Leave blank to auto-generate">
            <TextInput
              id="project-slug"
              className="mono"
              value={form.slug}
              onChange={(value) => patch({ slug: value })}
              placeholder="atlas-engine"
            />
          </FormField>
          <div className="admin-form__row">
            <FormField id="project-status" label="Status">
              <Select
                id="project-status"
                options={[
                  { value: 'draft', label: 'Draft' },
                  { value: 'published', label: 'Published' },
                  { value: 'archived', label: 'Archived' },
                ]}
                value={form.status}
                onChange={(value) => patch({ status: value as ProjectStatus })}
              />
            </FormField>
            <FormField id="project-type" label="Project type" required>
              <Select
                id="project-type"
                placeholder="Select a type"
                options={[
                  { value: 'client-work', label: 'Client work' },
                  { value: 'product', label: 'Product' },
                  { value: 'experiment', label: 'Experiment' },
                ]}
                value={form.project_type}
                onChange={(value) => patch({ project_type: value as ProjectType })}
              />
            </FormField>
            <FormField id="project-display-order" label="Display order">
              <TextInput
                id="project-display-order"
                type="number"
                min={0}
                inputMode="numeric"
                value={form.display_order}
                onChange={(value) => patch({ display_order: value })}
              />
            </FormField>
          </div>
          <FormField id="project-client" label="Client">
            <Select
              id="project-client"
              placeholder="No client"
              options={clientOptions}
              value={form.client_id}
              onChange={(value) => patch({ client_id: value })}
            />
          </FormField>
          <FormField id="project-category" label="Category">
            <TextInput
              id="project-category"
              value={form.category}
              onChange={(value) => patch({ category: value })}
              placeholder="AI"
            />
          </FormField>
          <FormField id="project-description" label="Description">
            <Textarea
              id="project-description"
              rows={5}
              value={form.description}
              onChange={(value) => patch({ description: value })}
            />
          </FormField>
          <FormField id="project-technologies" label="Technologies" hint="Comma separated">
            <TextInput
              id="project-technologies"
              value={form.technologies}
              onChange={(value) => patch({ technologies: value })}
              placeholder="Python, LLMs, FastAPI"
            />
          </FormField>
          <Checkbox
            id="project-featured"
            label="Featured"
            description="Featured projects surface on the home page."
            checked={form.featured}
            onChange={(value) => patch({ featured: value })}
          />
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Links &amp; dates</h2>
          <FormField id="project-live-url" label="Live URL">
            <TextInput
              id="project-live-url"
              type="url"
              value={form.live_url}
              onChange={(value) => patch({ live_url: value })}
              placeholder="https://example.com"
            />
          </FormField>
          <FormField id="project-github-url" label="Repository URL">
            <TextInput
              id="project-github-url"
              type="url"
              value={form.github_url}
              onChange={(value) => patch({ github_url: value })}
              placeholder="https://github.com/…"
            />
          </FormField>
          <FormField id="project-completion-date" label="Completion date">
            <TextInput
              id="project-completion-date"
              type="date"
              value={form.completion_date}
              onChange={(value) => patch({ completion_date: value })}
            />
          </FormField>
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Media</h2>
          <ImageUploadField
            id="project-thumbnail"
            label="Thumbnail"
            value={form.thumbnail_media_id}
            onChange={(mediaId) => patch({ thumbnail_media_id: mediaId })}
            upload={uploadMedia}
            resolvePreviewUrl={resolveAdminMediaPreviewUrl}
            className="admin-section__field"
          />
          <ImageGalleryField
            id="project-gallery"
            label="Gallery"
            value={form.gallery}
            onChange={(mediaIds) => patch({ gallery: mediaIds })}
            upload={uploadMedia}
            resolvePreviewUrl={resolveAdminMediaPreviewUrl}
            hint="Additional project images"
            className="admin-section__field"
          />
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Publishing</h2>
          <p className="admin-section__hint">
            {form.status === 'published'
              ? 'Published projects appear on the public site. Drafts and archived projects stay hidden.'
              : form.status === 'archived'
                ? 'Archived projects are hidden from the public site.'
                : 'This project is a draft and will stay hidden from the public site.'}
          </p>
          {previewable ? (
            <Link className="btn btn--ghost btn--sm" to={`/projects/${data?.slug}`} target="_blank" rel="noreferrer">
              View public page
            </Link>
          ) : null}
        </section>

        {saveError ? (
          <p className="form-field__error form-field__error--form" role="alert">
            {saveError}
          </p>
        ) : null}
        {dirty ? <p className="admin-form__dirty" role="status">Unsaved changes.</p> : null}

        <FormActions onCancel={handleCancel}>
          <SaveButton busy={saving}>{isNew ? 'Create project' : 'Save changes'}</SaveButton>
        </FormActions>
      </form>

      <p style={{ marginTop: 'var(--space-5)' }}>
        <Link className="btn btn--ghost btn--sm" to="/admin/projects">
          Back to projects
        </Link>
      </p>

      <ConfirmDialog
        open={discardOpen}
        title="Discard unsaved changes?"
        body="Your edits have not been saved and will be lost."
        confirmLabel="Discard"
        cancelLabel="Keep editing"
        danger
        onConfirm={() => navigate('/admin/projects')}
        onCancel={() => setDiscardOpen(false)}
      />
    </div>
  )
}