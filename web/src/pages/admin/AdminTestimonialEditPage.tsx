/**
 * Admin testimonial editor — create (`/admin/testimonials/new`) and edit
 * (`/admin/testimonials/:id`), with a live explanation of where the
 * testimonial will appear based on its publish/featured state.
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { useBeforeUnload } from '../../lib/hooks/useBeforeUnload'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { useAdminTestimonial } from '../../features/testimonials/hooks'
import { useAdminClients } from '../../features/clients/hooks'
import { createTestimonial, updateTestimonial } from '../../features/testimonials/api'
import { resolveAdminMediaPreviewUrl, uploadMedia } from '../../features/media/api'
import { PageHeader } from '../../components/admin/PageHeader'
import { FormField } from '../../components/form/FormField'
import { TextInput } from '../../components/form/TextInput'
import { Textarea } from '../../components/form/Textarea'
import { Select } from '../../components/form/Select'
import { Checkbox } from '../../components/form/Checkbox'
import { ImageUploadField } from '../../components/form/ImageUploadField'
import { FormActions } from '../../components/form/FormActions'
import { SaveButton } from '../../components/form/SaveButton'
import { ConfirmDialog } from '../../components/form/ConfirmDialog'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import type { TestimonialStatus } from '../../types'

const STATUS_OPTIONS: { value: TestimonialStatus; label: string }[] = [
  { value: 'pending', label: 'Pending review' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
]

export default function AdminTestimonialEditPage() {
  const { testimonialId = 'new' } = useParams()
  const isNew = testimonialId === 'new'
  usePageMeta({ title: `${isNew ? 'New testimonial' : 'Edit testimonial'} — Admin — Thridha Labs` })

  const navigate = useNavigate()
  const { data, loading, error, reload } = useAdminTestimonial(isNew ? undefined : testimonialId)
  useAdminSessionIssue(error)

  const clients = useAdminClients({ page: 1, page_size: 100, sort: 'name', order: 'asc' })
  useAdminSessionIssue(clients.error)

  const [form, setForm] = useState({
    client_id: '',
    person_name: '',
    role: '',
    company: '',
    testimonial_text: '',
    profile_image_media_id: null as string | null,
    rating: '5',
    featured: false,
    published: false,
    status: 'pending' as TestimonialStatus,
    display_order: '0',
    date: '',
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
      client_id: data.client_id ?? '',
      person_name: data.person_name,
      role: data.role ?? '',
      company: data.company ?? '',
      testimonial_text: data.testimonial_text,
      profile_image_media_id: data.profile_image_media_id,
      rating: String(data.rating),
      featured: data.featured,
      published: data.published,
      status: data.status,
      display_order: String(data.display_order),
      date: data.date ?? '',
    })
    setDirty(false)
  }, [data])

  function patch(p: Partial<typeof form>): void {
    setForm((prev) => ({ ...prev, ...p }))
    setDirty(true)
  }

  const visibility = useMemo(() => {
    if (form.status !== 'approved') {
      return "Not approved — this testimonial is hidden until approved."
    }
    if (!form.published) return "Approved but unpublished — appears nowhere on the public site."
    if (form.featured) return "Approved, published and featured — appears on the home page."
    return "Approved and published — appears on the testimonials page."
  }, [form.status, form.published, form.featured])

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    if (!form.person_name.trim()) {
      setSaveError('Person name is required.')
      return
    }
    if (!form.testimonial_text.trim()) {
      setSaveError('Testimonial text is required.')
      return
    }
    const payload = {
      client_id: form.client_id || null,
      person_name: form.person_name.trim(),
      role: form.role.trim(),
      company: form.company.trim() || null,
      testimonial_text: form.testimonial_text.trim(),
      profile_image_media_id: form.profile_image_media_id,
      rating: Number(form.rating || 5),
      featured: form.featured,
      published: form.published,
      status: form.status,
      display_order: Number(form.display_order || 0),
      date: form.date || null,
    }
    setSaving(true)
    setSaveError(null)
    try {
      if (isNew) {
        await createTestimonial(payload)
      } else {
        await updateTestimonial(testimonialId, payload)
      }
      setDirty(false)
      navigate('/admin/testimonials')
    } catch (caught) {
      setSaveError(getErrorMessage(caught, 'Could not save the testimonial.'))
    } finally {
      setSaving(false)
    }
  }

  function handleCancel(): void {
    if (dirty) {
      setDiscardOpen(true)
    } else {
      navigate('/admin/testimonials')
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
        title={isNew ? 'Add testimonial' : 'Edit testimonial'}
        description="A quote from a client or partner."
      />

      <form className="admin-form" onSubmit={handleSubmit} noValidate>
        <section className="admin-section">
          <h2 className="admin-section__title">Quote</h2>
          <FormField id="testimonial-person" label="Person name" required>
            <TextInput
              id="testimonial-person"
              value={form.person_name}
              onChange={(value) => patch({ person_name: value })}
              placeholder="Ada Lovelace"
            />
          </FormField>
          <FormField id="testimonial-role" label="Role / title">
            <TextInput
              id="testimonial-role"
              value={form.role}
              onChange={(value) => patch({ role: value })}
              placeholder="Partner"
            />
          </FormField>
          <FormField id="testimonial-company" label="Company">
            <TextInput
              id="testimonial-company"
              value={form.company}
              onChange={(value) => patch({ company: value })}
              placeholder="Acme Co"
            />
          </FormField>
          <FormField id="testimonial-client" label="Linked client">
            <Select
              id="testimonial-client"
              placeholder="No client"
              options={clientOptions}
              value={form.client_id}
              onChange={(value) => patch({ client_id: value })}
            />
          </FormField>
          <FormField id="testimonial-text" label="Testimonial text" required>
            <Textarea
              id="testimonial-text"
              rows={4}
              value={form.testimonial_text}
              onChange={(value) => patch({ testimonial_text: value })}
            />
          </FormField>
          <div className="admin-form__row">
            <FormField id="testimonial-rating" label="Rating">
              <Select
                id="testimonial-rating"
                options={[1, 2, 3, 4, 5].map((value) => ({ value: String(value), label: '★'.repeat(value) }))}
                value={form.rating}
                onChange={(value) => patch({ rating: value })}
              />
            </FormField>
            <FormField id="testimonial-date" label="Date">
              <TextInput
                id="testimonial-date"
                type="date"
                value={form.date}
                onChange={(value) => patch({ date: value })}
              />
            </FormField>
            <FormField id="testimonial-display-order" label="Display order">
              <TextInput
                id="testimonial-display-order"
                type="number"
                min={0}
                inputMode="numeric"
                value={form.display_order}
                onChange={(value) => patch({ display_order: value })}
              />
            </FormField>
          </div>
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Publication</h2>
          <FormField id="testimonial-status" label="Moderation status">
            <Select
              id="testimonial-status"
              options={STATUS_OPTIONS}
              value={form.status}
              onChange={(value) => patch({ status: value as TestimonialStatus })}
            />
          </FormField>
          <Checkbox
            id="testimonial-published"
            label="Published"
            description="Hidden from the public site until published."
            checked={form.published}
            onChange={(value) => patch({ published: value })}
            className="admin-section__field"
          />
          <Checkbox
            id="testimonial-featured"
            label="Featured"
            description="Boosts the testimonial to home-page surfaces."
            checked={form.featured}
            onChange={(value) => patch({ featured: value })}
            className="admin-section__field"
          />
          <p className="behavior-note behavior-note--live" role="status">
            {visibility}
          </p>
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Media</h2>
          <ImageUploadField
            id="testimonial-profile-image"
            label="Profile image"
            value={form.profile_image_media_id}
            onChange={(mediaId) => patch({ profile_image_media_id: mediaId })}
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
          <SaveButton busy={saving}>{isNew ? 'Create testimonial' : 'Save changes'}</SaveButton>
        </FormActions>
      </form>

      <p style={{ marginTop: 'var(--space-5)' }}>
        <Link className="btn btn--ghost btn--sm" to="/admin/testimonials">
          Back to testimonials
        </Link>
      </p>

      <ConfirmDialog
        open={discardOpen}
        title="Discard unsaved changes?"
        body="Your edits have not been saved and will be lost."
        confirmLabel="Discard"
        cancelLabel="Keep editing"
        danger
        onConfirm={() => navigate('/admin/testimonials')}
        onCancel={() => setDiscardOpen(false)}
      />
    </div>
  )
}