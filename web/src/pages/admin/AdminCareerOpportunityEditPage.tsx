/**
 * Admin opportunity editor — create (`/admin/careers/opportunities/new`) and
 * edit (`/admin/careers/opportunities/:id`).
 */

import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { useBeforeUnload } from '../../lib/hooks/useBeforeUnload'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { useAdminOpportunity, useAdminCareersSettings } from '../../features/careers/hooks'
import { createOpportunity, updateOpportunity } from '../../features/careers/api'
import { PageHeader } from '../../components/admin/PageHeader'
import { FormField } from '../../components/form/FormField'
import { TextInput } from '../../components/form/TextInput'
import { Textarea } from '../../components/form/Textarea'
import { Select } from '../../components/form/Select'
import { FormActions } from '../../components/form/FormActions'
import { SaveButton } from '../../components/form/SaveButton'
import { ConfirmDialog } from '../../components/form/ConfirmDialog'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import type { OpportunityStatus, OpportunityType, WorkMode } from '../../types'

const STATUS_LABELS: Record<OpportunityStatus, string> = {
  draft: 'Draft',
  open: 'Open',
  closed: 'Closed',
}

const TYPE_OPTIONS: Array<{ value: OpportunityType; label: string }> = [
  { value: 'lab-member', label: 'Lab Member' },
  { value: 'internship', label: 'Internship' },
  { value: 'full-time', label: 'Full-time' },
  { value: 'part-time', label: 'Part-time' },
  { value: 'contract', label: 'Contract' },
  { value: 'other', label: 'Other' },
]

const WORK_MODE_OPTIONS: Array<{ value: WorkMode; label: string }> = [
  { value: 'remote', label: 'Remote' },
  { value: 'on-site', label: 'On-site' },
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'flexible', label: 'Flexible' },
]

export default function AdminCareerOpportunityEditPage() {
  const { opportunityId = 'new' } = useParams()
  const isNew = opportunityId === 'new'
  usePageMeta({ title: `${isNew ? 'New opportunity' : 'Edit opportunity'} — Admin — Thridha Labs` })

  const navigate = useNavigate()
  const { data, loading, error, reload } = useAdminOpportunity(isNew ? undefined : opportunityId)
  useAdminSessionIssue(error)

  const settings = useAdminCareersSettings()
  useAdminSessionIssue(settings.error)

  const [form, setForm] = useState({
    title: '',
    slug: '',
    status: 'draft' as OpportunityStatus,
    type: '' as '' | OpportunityType,
    custom_type: '',
    work_mode: '' as '' | WorkMode,
    description: '',
    skills: '',
    application_email: '',
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
      title: data.title,
      slug: data.slug,
      status: data.status,
      type: data.type,
      custom_type: data.custom_type ?? '',
      work_mode: data.work_mode ?? '',
      description: data.description,
      skills: data.skills.join(', '),
      application_email: data.application_email ?? '',
      display_order: String(data.display_order),
    })
    setDirty(false)
  }, [data])

  function patch(patch: Partial<typeof form>): void {
    setForm((prev) => ({ ...prev, ...patch }))
    setDirty(true)
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    if (!form.title.trim()) {
      setSaveError('A title is required.')
      return
    }
    if (!form.type) {
      setSaveError('Choose a role type.')
      return
    }
    if (form.type === 'other' && !form.custom_type.trim()) {
      setSaveError('Enter a custom role type when “Other” is selected.')
      return
    }
    if (form.application_email.trim() && !form.application_email.includes('@')) {
      setSaveError('Enter a valid application email or leave it blank.')
      return
    }
    const payload = {
      title: form.title.trim(),
      slug: form.slug.trim() || null,
      status: form.status,
      type: form.type,
      custom_type: form.type === 'other' ? form.custom_type.trim() : null,
      work_mode: form.work_mode || null,
      description: form.description,
      skills: form.skills
        .split(',')
        .map((skill) => skill.trim())
        .filter(Boolean),
      application_email: form.application_email.trim() || null,
      display_order: Number(form.display_order || 0),
    }
    setSaving(true)
    setSaveError(null)
    try {
      if (isNew) {
        await createOpportunity(payload)
      } else {
        await updateOpportunity(opportunityId, payload)
      }
      setDirty(false)
      navigate('/admin/careers/opportunities')
    } catch (caught) {
      setSaveError(getErrorMessage(caught, 'Could not save the opportunity.'))
    } finally {
      setSaving(false)
    }
  }

  function handleCancel(): void {
    if (dirty) {
      setDiscardOpen(true)
    } else {
      navigate('/admin/careers/opportunities')
    }
  }

  const defaultEmail = settings.data?.application_email ?? ''
  const effectiveEmail = form.application_email.trim() || defaultEmail

  if (!isNew && loading) {
    return <ContentSkeleton rows={6} />
  }

  if (!isNew && error) {
    return <ErrorState error={error} onRetry={reload} />
  }

  const settingsReady = !settings.loading

  return (
    <div>
      <PageHeader
        eyebrow="Content"
        title={isNew ? 'Add opportunity' : 'Edit opportunity'}
        description={isNew ? 'Create a role open to the lab.' : 'Update opportunity details.'}
      />

      <form className="admin-form" onSubmit={handleSubmit} noValidate>
        <section className="admin-section">
          <h2 className="admin-section__title">Basics</h2>
          <FormField id="opportunity-title" label="Title" required>
            <TextInput
              id="opportunity-title"
              value={form.title}
              onChange={(value) => patch({ title: value })}
              placeholder="Lab Member"
            />
          </FormField>
          <FormField id="opportunity-slug" label="Slug" hint="Leave blank to auto-generate">
            <TextInput
              id="opportunity-slug"
              className="mono"
              value={form.slug}
              onChange={(value) => patch({ slug: value })}
              placeholder="lab-member"
            />
          </FormField>
          <div className="admin-form__row">
            <FormField id="opportunity-status" label="Status">
              <Select
                id="opportunity-status"
                options={Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label }))}
                value={form.status}
                onChange={(value) => patch({ status: value as OpportunityStatus })}
              />
            </FormField>
            <FormField id="opportunity-type" label="Role type" required>
              <Select
                id="opportunity-type"
                placeholder="Select a type"
                options={TYPE_OPTIONS}
                value={form.type}
                onChange={(value) => patch({ type: value as OpportunityType })}
              />
            </FormField>
            {form.type === 'other' ? (
              <FormField id="opportunity-custom-type" label="Custom role type" required>
                <TextInput
                  id="opportunity-custom-type"
                  value={form.custom_type}
                  onChange={(value) => patch({ custom_type: value })}
                  placeholder="Residency"
                />
              </FormField>
            ) : null}
            <FormField id="opportunity-display-order" label="Display order">
              <TextInput
                id="opportunity-display-order"
                type="number"
                min={0}
                inputMode="numeric"
                value={form.display_order}
                onChange={(value) => patch({ display_order: value })}
              />
            </FormField>
            <FormField id="opportunity-work-mode" label="Work mode">
              <Select
                id="opportunity-work-mode"
                placeholder="Not specified"
                options={WORK_MODE_OPTIONS}
                value={form.work_mode}
                onChange={(value) => patch({ work_mode: value as WorkMode })}
              />
            </FormField>
          </div>
          <FormField id="opportunity-description" label="Description" required>
            <Textarea
              id="opportunity-description"
              rows={5}
              value={form.description}
              onChange={(value) => patch({ description: value })}
            />
          </FormField>
          <FormField id="opportunity-skills" label="Skills" hint="Comma separated">
            <TextInput
              id="opportunity-skills"
              value={form.skills}
              onChange={(value) => patch({ skills: value })}
              placeholder="Python, LLMs, FastAPI"
            />
          </FormField>
          <FormField
            id="opportunity-email"
            label="Application email"
            hint={defaultEmail ? `Falls back to ${defaultEmail}` : 'Falls back to the careers default when set'}
          >
            <TextInput
              id="opportunity-email"
              type="email"
              value={form.application_email}
              onChange={(value) => patch({ application_email: value })}
              placeholder="apply@thridhalabs.com"
            />
          </FormField>
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Publishing</h2>
          <p className="admin-section__hint">
            {form.status === 'open'
              ? 'Open opportunities appear on the public careers page. Drafts and closed roles stay hidden.'
              : form.status === 'closed'
                ? 'Closed opportunities are hidden from the public site but kept on file.'
                : 'This opportunity is a draft and will stay hidden from the public site.'}
          </p>
          {form.status === 'open' && settingsReady && !effectiveEmail ? (
            <p className="admin-section__hint" role="alert">
              This role is open but no application email resolves (neither an override here nor the
              careers default) — the public Apply link will be hidden.
            </p>
          ) : null}
        </section>

        {saveError ? (
          <p className="form-field__error form-field__error--form" role="alert">
            {saveError}
          </p>
        ) : null}
        {dirty ? <p className="admin-form__dirty" role="status">Unsaved changes.</p> : null}

        <FormActions onCancel={handleCancel}>
          <SaveButton busy={saving}>{isNew ? 'Create opportunity' : 'Save changes'}</SaveButton>
        </FormActions>
      </form>

      <p style={{ marginTop: 'var(--space-5)' }}>
        <Link className="btn btn--ghost btn--sm" to="/admin/careers/opportunities">
          Back to opportunities
        </Link>
      </p>

      <ConfirmDialog
        open={discardOpen}
        title="Discard unsaved changes?"
        body="Your edits have not been saved and will be lost."
        confirmLabel="Discard"
        cancelLabel="Keep editing"
        danger
        onConfirm={() => navigate('/admin/careers/opportunities')}
        onCancel={() => setDiscardOpen(false)}
      />
    </div>
  )
}