/**
 * Admin careers — the careers settings singleton. Turning the Toggle on makes
 * the Careers page and its nav/footer links appear; the application email and
 * template drive the public "Apply by email" links.
 */

import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { useBeforeUnload } from '../../lib/hooks/useBeforeUnload'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { useAdminCareersSettings } from '../../features/careers/hooks'
import { updateCareersSettings } from '../../features/careers/api'
import { PageHeader } from '../../components/admin/PageHeader'
import { FormField } from '../../components/form/FormField'
import { TextInput } from '../../components/form/TextInput'
import { Textarea } from '../../components/form/Textarea'
import { Toggle } from '../../components/form/Toggle'
import { FormActions } from '../../components/form/FormActions'
import { SaveButton } from '../../components/form/SaveButton'
import { ConfirmDialog } from '../../components/form/ConfirmDialog'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'

export default function AdminCareersPage() {
  usePageMeta({ title: 'Careers — Admin — Thridha Labs' })

  const { data, loading, error, reload } = useAdminCareersSettings()
  useAdminSessionIssue(error)

  const navigate = useNavigate()

  const [form, setForm] = useState({
    enabled: false,
    heading: '',
    description: '',
    application_email: '',
    application_template: '',
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
      enabled: data.enabled,
      heading: data.heading ?? '',
      description: data.description ?? '',
      application_email: data.application_email ?? '',
      application_template: data.application_template ?? '',
    })
    setDirty(false)
  }, [data])

  function patch(patch: Partial<typeof form>): void {
    setForm((prev) => ({ ...prev, ...patch }))
    setDirty(true)
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    if (form.enabled && form.application_email.trim() && !form.application_email.includes('@')) {
      setSaveError('Enter a valid application email or leave it blank for now.')
      return
    }
    setSaving(true)
    setSaveError(null)
    try {
      await updateCareersSettings({
        enabled: form.enabled,
        heading: form.heading.trim() || null,
        description: form.description.trim() || null,
        application_email: form.application_email.trim() || null,
        application_template: form.application_template.trim() || null,
      })
      await reload()
      setDirty(false)
    } catch (caught) {
      setSaveError(getErrorMessage(caught, 'Could not save careers settings.'))
    } finally {
      setSaving(false)
    }
  }

  function handleCancel(): void {
    if (dirty) {
      setDiscardOpen(true)
    } else {
      navigate('/admin')
    }
  }

  if (loading || !data) {
    return <ContentSkeleton rows={4} />
  }

  if (error) {
    return <ErrorState error={error} onRetry={reload} />
  }

  return (
    <div>
      <PageHeader
        eyebrow="Content"
        title="Careers"
        description="The public careers page and how people can apply."
        actionLabel="Manage opportunities"
        actionTo="/admin/careers/opportunities"
      />

      <form className="admin-form" onSubmit={handleSubmit} noValidate>
        <section className="admin-section">
          <h2 className="admin-section__title">Availability</h2>
          <Toggle
            id="careers-enabled"
            label="Careers page enabled"
            description="Shows the Careers link in the public navigation and serves the page. Disabling hides everything."
            checked={form.enabled}
            onChange={(value) => patch({ enabled: value })}
          />
          {form.enabled && !form.application_email.trim() ? (
            <p className="admin-section__hint" role="alert">
              No default application email yet — public Apply links will be hidden until one is set
              here or on an opportunity.
            </p>
          ) : null}
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Presentation</h2>
          <FormField id="careers-heading" label="Heading" hint="Defaults to “Open roles at the lab”">
            <TextInput
              id="careers-heading"
              value={form.heading}
              onChange={(value) => patch({ heading: value })}
              placeholder="Open roles at the lab"
            />
          </FormField>
          <FormField id="careers-description" label="Intro">
            <Textarea
              id="careers-description"
              rows={3}
              value={form.description}
              onChange={(value) => patch({ description: value })}
            />
          </FormField>
          <FormField id="careers-email" label="Application email" hint="Falls back to this when an opportunity has no email of its own">
            <TextInput
              id="careers-email"
              type="email"
              value={form.application_email}
              onChange={(value) => patch({ application_email: value })}
              placeholder="apply@thridhalabs.com"
            />
          </FormField>
          <FormField id="careers-template" label="Application template" hint="Pre-filled body of the apply email">
            <Textarea
              id="careers-template"
              rows={4}
              value={form.application_template}
              onChange={(value) => patch({ application_template: value })}
              placeholder="Tell us about yourself and what you would like to build."
            />
          </FormField>
        </section>

        {saveError ? (
          <p className="form-field__error form-field__error--form" role="alert">
            {saveError}
          </p>
        ) : null}
        {dirty ? <p className="admin-form__dirty" role="status">Unsaved changes.</p> : null}

        <FormActions onCancel={handleCancel} cancelLabel="Discard">
          <SaveButton busy={saving}>Save careers settings</SaveButton>
        </FormActions>
      </form>

      <ConfirmDialog
        open={discardOpen}
        title="Discard unsaved changes?"
        body="Your edits have not been saved and will be lost."
        confirmLabel="Discard"
        cancelLabel="Keep editing"
        danger
        onConfirm={() => navigate('/admin')}
        onCancel={() => setDiscardOpen(false)}
      />
    </div>
  )
}