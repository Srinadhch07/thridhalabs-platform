/**
 * Admin client editor — create (`/admin/clients/new`) and edit
 * (`/admin/clients/:id`).
 */

import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { useBeforeUnload } from '../../lib/hooks/useBeforeUnload'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { useAdminClient } from '../../features/clients/hooks'
import { createClient, updateClient } from '../../features/clients/api'
import { resolveAdminMediaPreviewUrl, uploadMedia } from '../../features/media/api'
import { PageHeader } from '../../components/admin/PageHeader'
import { FormField } from '../../components/form/FormField'
import { TextInput } from '../../components/form/TextInput'
import { Textarea } from '../../components/form/Textarea'
import { Checkbox } from '../../components/form/Checkbox'
import { ImageUploadField } from '../../components/form/ImageUploadField'
import { FormActions } from '../../components/form/FormActions'
import { SaveButton } from '../../components/form/SaveButton'
import { ConfirmDialog } from '../../components/form/ConfirmDialog'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import type { AdminClient } from '../../types'

export default function AdminClientEditPage() {
  const { clientId = 'new' } = useParams()
  const isNew = clientId === 'new'
  usePageMeta({ title: `${isNew ? 'New client' : 'Edit client'} — Admin — Thridha Labs` })

  const navigate = useNavigate()
  const { data, loading, error, reload } = useAdminClient(isNew ? undefined : clientId)
  useAdminSessionIssue(error)

  const [form, setForm] = useState({
    name: '',
    slug: '',
    website: '',
    industry: '',
    category: '',
    description: '',
    logo_media_id: null as string | null,
    featured_image_media_id: null as string | null,
    featured: false,
    display_order: '0',
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
      website: data.website ?? '',
      industry: data.industry ?? '',
      category: data.category ?? '',
      description: data.description ?? '',
      logo_media_id: data.logo_media_id,
      featured_image_media_id: data.featured_image_media_id,
      featured: data.featured,
      display_order: String(data.display_order),
    })
    setDirty(false)
  }, [data])

  function patch(p: Partial<typeof form>): void {
    setForm((prev) => ({ ...prev, ...p }))
    setDirty(true)
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    const payload = {
      name: form.name.trim(),
      slug: form.slug.trim() || null,
      website: form.website.trim() || null,
      industry: form.industry.trim() || null,
      category: form.category.trim() || null,
      description: form.description,
      logo_media_id: form.logo_media_id,
      featured_image_media_id: form.featured_image_media_id,
      featured: form.featured,
      display_order: Number(form.display_order || 0),
    }
    setSaving(true)
    setSaveError(null)
    try {
      if (isNew) {
        await createClient(payload)
      } else {
        await updateClient(clientId, payload)
      }
      setDirty(false)
      navigate('/admin/clients')
    } catch (caught) {
      setSaveError(getErrorMessage(caught, 'Could not save the client.'))
    } finally {
      setSaving(false)
    }
  }

  function handleCancel(): void {
    if (dirty) {
      setDiscardOpen(true)
    } else {
      navigate('/admin/clients')
    }
  }

  if (!isNew && loading) {
    return <ContentSkeleton rows={5} />
  }

  if (!isNew && error) {
    return <ErrorState error={error} onRetry={reload} />
  }

  return (
    <div>
      <PageHeader
        eyebrow="Content"
        title={isNew ? 'Add client' : `Edit client`}
        description={isNew ? 'Create a new client.' : `Editing ${(data as AdminClient | null)?.name ?? 'client'}.`}
      />

      <form className="admin-form" onSubmit={handleSubmit} noValidate>
        <section className="admin-section">
          <h2 className="admin-section__title">Details</h2>
          <FormField id="client-name" label="Name" required>
            <TextInput
              id="client-name"
              value={form.name}
              onChange={(value) => patch({ name: value })}
              placeholder="Acme Co"
            />
          </FormField>
          <FormField id="client-slug" label="Slug" hint="Leave blank to auto-generate">
            <TextInput
              id="client-slug"
              className="mono"
              value={form.slug}
              onChange={(value) => patch({ slug: value })}
              placeholder="acme-co"
            />
          </FormField>
          <FormField id="client-industry" label="Industry">
            <TextInput
              id="client-industry"
              value={form.industry}
              onChange={(value) => patch({ industry: value })}
              placeholder="Energy"
            />
          </FormField>
          <FormField id="client-category" label="Category">
            <TextInput
              id="client-category"
              value={form.category}
              onChange={(value) => patch({ category: value })}
            />
          </FormField>
          <FormField id="client-website" label="Website">
            <TextInput
              id="client-website"
              type="url"
              value={form.website}
              onChange={(value) => patch({ website: value })}
              placeholder="https://example.com"
            />
          </FormField>
          <FormField id="client-description" label="Description">
            <Textarea
              id="client-description"
              rows={4}
              value={form.description}
              onChange={(value) => patch({ description: value })}
            />
          </FormField>
          <FormField id="client-display-order" label="Display order">
            <TextInput
              id="client-display-order"
              type="number"
              min={0}
              inputMode="numeric"
              value={form.display_order}
              onChange={(value) => patch({ display_order: value })}
            />
          </FormField>
          <Checkbox
            id="client-featured"
            label="Featured"
            description="Featured clients surface on the home page."
            checked={form.featured}
            onChange={(value) => patch({ featured: value })}
          />
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Media</h2>
          <ImageUploadField
            id="client-logo"
            label="Logo"
            value={form.logo_media_id}
            onChange={(mediaId) => patch({ logo_media_id: mediaId })}
            upload={uploadMedia}
            resolvePreviewUrl={resolveAdminMediaPreviewUrl}
            className="admin-section__field"
          />
          <ImageUploadField
            id="client-featured-image"
            label="Featured image"
            value={form.featured_image_media_id}
            onChange={(mediaId) => patch({ featured_image_media_id: mediaId })}
            upload={uploadMedia}
            resolvePreviewUrl={resolveAdminMediaPreviewUrl}
            className="admin-section__field"
          />
        </section>

        {saveError ? (
          <p className="form-field__error form-field__error--form" role="alert">
            {saveError}
          </p>
        ) : null}
        {dirty ? <p className="admin-form__dirty" role="status">Unsaved changes.</p> : null}

        <FormActions onCancel={handleCancel}>
          <SaveButton busy={saving}>{isNew ? 'Create client' : 'Save changes'}</SaveButton>
        </FormActions>
      </form>

      <p style={{ marginTop: 'var(--space-5)' }}>
        <Link className="btn btn--ghost btn--sm" to="/admin/clients">
          Back to clients
        </Link>
      </p>

      <ConfirmDialog
        open={discardOpen}
        title="Discard unsaved changes?"
        body="Your edits have not been saved and will be lost."
        confirmLabel="Discard"
        cancelLabel="Keep editing"
        danger
        onConfirm={() => navigate('/admin/clients')}
        onCancel={() => setDiscardOpen(false)}
      />
    </div>
  )
}