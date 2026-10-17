/**
 * Admin activity editor — create (`/admin/activities/new`) and edit
 * (`/admin/activities/:activityId`).
 *
 * Create/update covers the core record. Brief upload and the participant /
 * invitation roster are only available once the activity exists.
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { useBeforeUnload } from '../../lib/hooks/useBeforeUnload'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { useAdminActivity } from '../../features/activities/hooks'
import {
  createAdminActivity,
  downloadAdminActivityBrief,
  removeActivityBrief,
  updateAdminActivity,
  uploadActivityBrief,
} from '../../features/activities/api'
import { resolveAdminMediaPreviewUrl, uploadMedia } from '../../features/media/api'
import {
  ACTIVITY_STATUS_LABELS,
  ACTIVITY_TYPE_LABELS,
  PRESENTATION_LABELS,
} from '../../features/activities/labels'
import { PageHeader } from '../../components/admin/PageHeader'
import { ActivityInvitationsPanel } from '../../components/admin/ActivityInvitationsPanel'
import { ActivityParticipantsPanel } from '../../components/admin/ActivityParticipantsPanel'
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
import type { ActivityStatus, ActivityType } from '../../types/activity'

/** Banner previews use the large variant so the 16:9 frame stays sharp. */
function resolveBannerPreviewUrl(mediaId: string): Promise<string | null> {
  return resolveAdminMediaPreviewUrl(mediaId, 'lg')
}

export default function AdminActivityEditPage() {
  const { activityId = 'new' } = useParams()
  const isNew = activityId === 'new'
  usePageMeta({ title: `${isNew ? 'New activity' : 'Edit activity'} — Admin — Thridha Labs` })

  const navigate = useNavigate()
  const { data, loading, error, reload } = useAdminActivity(isNew ? undefined : activityId)
  useAdminSessionIssue(error)

  const [form, setForm] = useState({
    title: '',
    slug: '',
    activity_type: '' as '' | ActivityType,
    status: 'draft' as ActivityStatus,
    summary: '',
    description: '',
    start_date: '',
    end_date: '',
    banner_media_id: null as string | null,
    featured: false,
    display_order: '0',
    roles_offered: '',
    tags: '',
    cancel_reason: '',
  })

  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [discardOpen, setDiscardOpen] = useState(false)

  // Brief sub-state
  const briefFileRef = useRef<HTMLInputElement>(null)
  const [briefBusy, setBriefBusy] = useState(false)
  const [briefError, setBriefError] = useState<string | null>(null)

  useBeforeUnload(dirty)

  const hydrated = useRef(false)
  useEffect(() => {
    if (!data || hydrated.current) return
    hydrated.current = true
    setForm({
      title: data.title,
      slug: data.slug,
      activity_type: data.activity_type,
      status: data.status,
      summary: data.summary,
      description: data.description,
      start_date: data.start_date ?? '',
      end_date: data.end_date ?? '',
      banner_media_id: data.banner_media_id,
      featured: data.featured,
      display_order: String(data.display_order),
      roles_offered: data.roles_offered.join(', '),
      tags: data.tags.join(', '),
      cancel_reason: data.cancel_reason ?? '',
    })
    setDirty(false)
  }, [data])

  function patch(p: Partial<typeof form>): void {
    setForm((prev) => ({ ...prev, ...p }))
    setDirty(true)
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    if (!form.title.trim()) {
      setSaveError('A title is required.')
      return
    }
    if (!form.activity_type) {
      setSaveError('Choose an activity type.')
      return
    }
    const payload = {
      title: form.title.trim(),
      slug: form.slug.trim() || null,
      activity_type: form.activity_type,
      status: form.status,
      summary: form.summary,
      description: form.description,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
      banner_media_id: form.banner_media_id,
      featured: form.featured,
      display_order: Number(form.display_order || 0),
      roles_offered: form.roles_offered
        .split(',')
        .map((role) => role.trim())
        .filter(Boolean),
      tags: form.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean),
      cancel_reason: form.status === 'cancelled' ? form.cancel_reason.trim() || null : null,
    }
    setSaving(true)
    setSaveError(null)
    try {
      if (isNew) {
        const created = await createAdminActivity(payload)
        setDirty(false)
        navigate(`/admin/activities/${created.id}`)
      } else {
        await updateAdminActivity(activityId, payload)
        setDirty(false)
        await reload()
      }
    } catch (caught) {
      setSaveError(getErrorMessage(caught, 'Could not save the activity.'))
    } finally {
      setSaving(false)
    }
  }

  function handleCancel(): void {
    if (dirty) {
      setDiscardOpen(true)
    } else {
      navigate('/admin/activities')
    }
  }

  async function handleBriefUpload(file: File | undefined): Promise<void> {
    if (!file || !data) return
    setBriefBusy(true)
    setBriefError(null)
    try {
      await uploadActivityBrief(data.id, file)
      await reload()
    } catch (caught) {
      setBriefError(getErrorMessage(caught, 'Could not upload the brief.'))
    } finally {
      setBriefBusy(false)
    }
  }

  async function handleBriefRemove(): Promise<void> {
    if (!data) return
    setBriefBusy(true)
    setBriefError(null)
    try {
      await removeActivityBrief(data.id)
      await reload()
    } catch (caught) {
      setBriefError(getErrorMessage(caught, 'Could not remove the brief.'))
    } finally {
      setBriefBusy(false)
    }
  }

  async function handleBriefOpen(): Promise<void> {
    if (!data) return
    setBriefBusy(true)
    setBriefError(null)
    try {
      const file = await downloadAdminActivityBrief(data.id)
      const url = URL.createObjectURL(file.blob)
      window.open(url, '_blank', 'noopener')
      setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch (caught) {
      setBriefError(getErrorMessage(caught, 'Could not open the brief.'))
    } finally {
      setBriefBusy(false)
    }
  }

  const typeOptions = useMemo(
    () => (Object.keys(ACTIVITY_TYPE_LABELS) as ActivityType[]).map((value) => ({ value, label: ACTIVITY_TYPE_LABELS[value] })),
    [],
  )
  const statusOptions = useMemo(
    () =>
      (Object.keys(ACTIVITY_STATUS_LABELS) as ActivityStatus[]).map((value) => ({
        value,
        label: ACTIVITY_STATUS_LABELS[value],
      })),
    [],
  )

  if (!isNew && loading) return <ContentSkeleton rows={6} />
  if (!isNew && error) return <ErrorState error={error} onRetry={reload} />

  const isProject = form.activity_type === 'project'
  const publicPath = data && data.status === 'published' ? `/activities/${data.slug}` : null

  return (
    <div>
      <PageHeader
        eyebrow="Programmes"
        title={isNew ? 'Add activity' : 'Edit activity'}
        description={isNew ? 'Create a project, programme or hackathon.' : 'Update activity details.'}
      />

      {data ? (
        <p className="admin-section__hint">
          Presentation: <strong>{PRESENTATION_LABELS[data.presentation_status]}</strong>
          {data.brief ? ` · Brief v${data.brief.version}` : ''}
        </p>
      ) : null}

      <form className="admin-form" onSubmit={handleSubmit} noValidate>
        <section className="admin-section">
          <h2 className="admin-section__title">Basics</h2>
          <FormField id="activity-title" label="Title" required>
            <TextInput
              id="activity-title"
              value={form.title}
              onChange={(value) => patch({ title: value })}
              placeholder="AI Builders Programme 2026"
            />
          </FormField>
          <FormField id="activity-slug" label="Slug" hint="Leave blank to auto-generate">
            <TextInput
              id="activity-slug"
              className="mono"
              value={form.slug}
              onChange={(value) => patch({ slug: value })}
              placeholder="ai-builders-programme-2026"
            />
          </FormField>
          <div className="admin-form__row">
            <FormField id="activity-type" label="Type" required>
              <Select
                id="activity-type"
                placeholder="Select a type"
                options={typeOptions}
                value={form.activity_type}
                onChange={(value) => patch({ activity_type: value as ActivityType })}
              />
            </FormField>
            <FormField id="activity-status" label="Status">
              <Select
                id="activity-status"
                options={statusOptions}
                value={form.status}
                onChange={(value) => patch({ status: value as ActivityStatus })}
              />
            </FormField>
            <FormField id="activity-display-order" label="Display order">
              <TextInput
                id="activity-display-order"
                type="number"
                min={0}
                inputMode="numeric"
                value={form.display_order}
                onChange={(value) => patch({ display_order: value })}
              />
            </FormField>
          </div>
          <FormField id="activity-summary" label="Summary" hint="Shown in cards and search results">
            <TextInput
              id="activity-summary"
              value={form.summary}
              onChange={(value) => patch({ summary: value })}
              placeholder="A four-week programme for applied AI builders."
            />
          </FormField>
          <FormField id="activity-description" label="Description">
            <Textarea
              id="activity-description"
              rows={6}
              value={form.description}
              onChange={(value) => patch({ description: value })}
            />
          </FormField>
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Schedule</h2>
          <div className="admin-form__row">
            <FormField id="activity-start" label="Start date">
              <TextInput
                id="activity-start"
                type="date"
                value={form.start_date}
                onChange={(value) => patch({ start_date: value })}
              />
            </FormField>
            <FormField id="activity-end" label="End date">
              <TextInput
                id="activity-end"
                type="date"
                value={form.end_date}
                onChange={(value) => patch({ end_date: value })}
              />
            </FormField>
          </div>
          <p className="admin-section__hint">
            Upcoming / ongoing / completed is derived from these dates; cancel or archive explicitly.
          </p>
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Details</h2>
          <FormField id="activity-roles" label="Roles offered" hint="Comma separated; used for project invitations">
            <TextInput
              id="activity-roles"
              value={form.roles_offered}
              onChange={(value) => patch({ roles_offered: value })}
              placeholder="Product Analyst, Frontend Developer, Backend Developer, AI Engineer"
            />
          </FormField>
          <FormField id="activity-tags" label="Tags" hint="Comma separated">
            <TextInput
              id="activity-tags"
              value={form.tags}
              onChange={(value) => patch({ tags: value })}
              placeholder="AI, cohort, remote"
            />
          </FormField>
          {form.status === 'cancelled' ? (
            <FormField id="activity-cancel-reason" label="Cancellation note">
              <TextInput
                id="activity-cancel-reason"
                value={form.cancel_reason}
                onChange={(value) => patch({ cancel_reason: value })}
                placeholder="Why was this cancelled?"
              />
            </FormField>
          ) : null}
          <Checkbox
            id="activity-featured"
            label="Featured on homepage"
            description="Published, featured activities appear in the homepage carousel."
            checked={form.featured}
            onChange={(value) => patch({ featured: value })}
          />
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Banner</h2>
          <ImageUploadField
            id="activity-banner"
            label="Promotional banner"
            value={form.banner_media_id}
            onChange={(mediaId) => patch({ banner_media_id: mediaId })}
            upload={uploadMedia}
            resolvePreviewUrl={resolveBannerPreviewUrl}
            aspectRatio="16 / 9"
            hint="A wide banner (e.g. 16:9 or wider) looks best. The whole image is shown uncropped on the public site and cards."
            className="admin-section__field"
          />
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Publishing</h2>
          <p className="admin-section__hint">
            {form.status === 'published'
              ? isProject
                ? 'Published — public page live; invitations available below.'
                : 'Published — members can self-register from the member portal.'
              : form.status === 'cancelled'
                ? 'Cancelled — kept reachable but clearly marked and never promoted.'
                : form.status === 'archived'
                  ? 'Archived — hidden from the public site and the homepage.'
                  : 'Draft — hidden from the public site.'}
          </p>
          {publicPath ? (
            <Link className="btn btn--ghost btn--sm" to={publicPath} target="_blank" rel="noreferrer">
              View public page
            </Link>
          ) : null}
        </section>

        {saveError ? (
          <p className="form-field__error form-field__error--form" role="alert">
            {saveError}
          </p>
        ) : null}
        {dirty ? (
          <p className="admin-form__dirty" role="status">
            Unsaved changes.
          </p>
        ) : null}

        <FormActions onCancel={handleCancel}>
          <SaveButton busy={saving}>{isNew ? 'Create activity' : 'Save changes'}</SaveButton>
        </FormActions>
      </form>

      {!isNew && data ? (
        <section className="admin-section">
          <h2 className="admin-section__title">PDF brief</h2>
          {data.brief ? (
            <p className="admin-section__hint">
              Current: v{data.brief.version} · {data.brief.filename} ·{' '}
              {Math.round(data.brief.size_bytes / 1024)} KB
              {data.brief_history_count > 1 ? ` · ${data.brief_history_count - 1} earlier version(s)` : ''}
            </p>
          ) : (
            <p className="admin-section__hint">No brief uploaded yet. PDF only.</p>
          )}
          <input
            ref={briefFileRef}
            id="activity-brief-input"
            type="file"
            accept="application/pdf"
            className="visually-hidden"
            disabled={briefBusy}
            onChange={(event) => {
              const file = event.target.files?.[0]
              event.target.value = ''
              void handleBriefUpload(file)
            }}
          />
          <div className="admin-table__actions">
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              disabled={briefBusy}
              onClick={() => briefFileRef.current?.click()}
            >
              {data.brief ? 'Replace brief' : 'Upload brief'}
            </button>
            {data.brief ? (
              <>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  disabled={briefBusy}
                  onClick={() => void handleBriefOpen()}
                >
                  Open
                </button>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  disabled={briefBusy}
                  onClick={() => void handleBriefRemove()}
                >
                  Remove
                </button>
              </>
            ) : null}
          </div>
          {briefError ? (
            <p className="form-field__error" role="alert">
              {briefError}
            </p>
          ) : null}
        </section>
      ) : null}

      {!isNew && data && isProject && data.status === 'published' ? (
        <ActivityInvitationsPanel
          activityId={data.id}
          roleOptions={data.roles_offered}
          onInvited={() => void reload()}
        />
      ) : null}

      {!isNew && data ? <ActivityParticipantsPanel activityId={data.id} /> : null}

      <p style={{ marginTop: 'var(--space-5)' }}>
        <Link className="btn btn--ghost btn--sm" to="/admin/activities">
          Back to activities
        </Link>
      </p>

      <ConfirmDialog
        open={discardOpen}
        title="Discard unsaved changes?"
        body="Your edits have not been saved and will be lost."
        confirmLabel="Discard"
        cancelLabel="Keep editing"
        danger
        onConfirm={() => navigate('/admin/activities')}
        onCancel={() => setDiscardOpen(false)}
      />
    </div>
  )
}
