/**
 * Admin settings — general, contact, social, footer, SEO, technical
 * (maintenance) and analytics sub-sections. Saves the full singleton via PUT.
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { useBeforeUnload } from '../../lib/hooks/useBeforeUnload'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { useAdminSettings } from '../../features/settings/hooks'
import { updateSettings } from '../../features/settings/api'
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

interface SocialRow {
  key: string
  url: string
}

function socialToRows(urls: Record<string, string>): SocialRow[] {
  return Object.entries(urls ?? {}).map(([key, url]) => ({ key, url }))
}

function rowsToSocial(rows: SocialRow[]): Record<string, string> {
  const out: Record<string, string> = {}
  for (const row of rows) {
    const key = row.key.trim().toLowerCase()
    if (key) out[key] = row.url.trim()
  }
  return out
}

const EMPTY_SOCIAL: SocialRow[] = []

export default function AdminSettingsPage() {
  usePageMeta({ title: 'Settings — Admin — Thridha Labs' })

  const { data, loading, error, reload } = useAdminSettings()
  useAdminSessionIssue(error)

  const navigate = useNavigate()

  const [general, setGeneral] = useState({ site_name: '', tagline: '', description: '' })
  const [contact, setContact] = useState({ contact_email: '', contact_phone: '', whatsapp: '', address: '' })
  const [social, setSocial] = useState<SocialRow[]>(EMPTY_SOCIAL)
  const [footer, setFooter] = useState({ copyright_text: '' })
  const [seo, setSeo] = useState({ seo_title: '', seo_description: '', seo_keywords: '' })
  const [analytics, setAnalytics] = useState({ google_verification: '', google_analytics: '' })
  const [maintenanceMode, setMaintenanceMode] = useState(false)

  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [discardOpen, setDiscardOpen] = useState(false)
  const [maintenanceConfirmOpen, setMaintenanceConfirmOpen] = useState(false)
  useBeforeUnload(dirty)

  const snapshot = useMemo(() => {
    if (!data) return null
    return {
      general: {
        site_name: data.general.site_name,
        tagline: data.general.tagline,
        description: data.general.description,
      },
      contact: {
        contact_email: data.contact.contact_email ?? '',
        contact_phone: data.contact.contact_phone ?? '',
        whatsapp: data.contact.whatsapp ?? '',
        address: data.contact.address ?? '',
      },
      social: socialToRows(data.social.urls),
      footer: { copyright_text: data.footer.copyright_text },
      seo: {
        seo_title: data.seo.seo_title,
        seo_description: data.seo.seo_description,
        seo_keywords: data.seo.seo_keywords.join(', '),
      },
      analytics: {
        google_verification: data.analytics.google_verification ?? '',
        google_analytics: data.analytics.google_analytics ?? '',
      },
      maintenanceMode: data.maintenance_mode,
    }
  }, [data])

  const hydrated = useRef(false)
  useEffect(() => {
    if (!snapshot || hydrated.current) return
    hydrated.current = true
    setGeneral(snapshot.general)
    setContact(snapshot.contact)
    setSocial(snapshot.social)
    setFooter(snapshot.footer)
    setSeo(snapshot.seo)
    setAnalytics(snapshot.analytics)
    setMaintenanceMode(snapshot.maintenanceMode)
    setDirty(false)
  }, [snapshot])

  function markDirty(): void {
    setDirty(true)
  }

  function updateGeneral(patch: Partial<typeof general>): void {
    setGeneral((prev) => ({ ...prev, ...patch }))
    markDirty()
  }

  function updateContact(patch: Partial<typeof contact>): void {
    setContact((prev) => ({ ...prev, ...patch }))
    markDirty()
  }

  function updateSocial(index: number, patch: Partial<SocialRow>): void {
    setSocial((prev) => prev.map((row, i) => (i === index ? { ...row, ...patch } : row)))
    markDirty()
  }

  function addSocial(): void {
    setSocial((prev) => [...prev, { key: '', url: '' }])
    markDirty()
  }

  function removeSocial(index: number): void {
    setSocial((prev) => prev.filter((_, i) => i !== index))
    markDirty()
  }

  function updateSeo(patch: Partial<typeof seo>): void {
    setSeo((prev) => ({ ...prev, ...patch }))
    markDirty()
  }

  function updateAnalytics(patch: Partial<typeof analytics>): void {
    setAnalytics((prev) => ({ ...prev, ...patch }))
    markDirty()
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    setSaving(true)
    setSaveError(null)
    try {
      const payload = {
        general,
        contact: {
          contact_email: contact.contact_email.trim() || null,
          contact_phone: contact.contact_phone.trim() || null,
          whatsapp: contact.whatsapp.trim() || null,
          address: contact.address.trim() || null,
        },
        social: { urls: rowsToSocial(social) },
        footer,
        seo: {
          ...seo,
          seo_keywords: seo.seo_keywords
            .split(',')
            .map((keyword) => keyword.trim())
            .filter(Boolean),
        },
        analytics: {
          google_verification: analytics.google_verification.trim() || null,
          google_analytics: analytics.google_analytics.trim() || null,
        },
        maintenance_mode: maintenanceMode,
      }
      await updateSettings(payload)
      await reload()
      setDirty(false)
    } catch (caught) {
      setSaveError(getErrorMessage(caught, 'Could not save settings.'))
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
    return <ContentSkeleton rows={6} />
  }

  if (error) {
    return <ErrorState error={error} onRetry={reload} />
  }

  return (
    <div>
      <PageHeader
        eyebrow="Configuration"
        title="Settings"
        description="General, contact, social, footer, SEO and technical settings."
      />

      <form className="admin-form" onSubmit={handleSubmit} noValidate>
        <section className="admin-section">
          <h2 className="admin-section__title">General</h2>
          <FormField id="settings-site-name" label="Site name" required>
            <TextInput
              id="settings-site-name"
              value={general.site_name}
              onChange={(value) => updateGeneral({ site_name: value })}
            />
          </FormField>
          <FormField id="settings-tagline" label="Tagline">
            <TextInput
              id="settings-tagline"
              value={general.tagline}
              onChange={(value) => updateGeneral({ tagline: value })}
            />
          </FormField>
          <FormField id="settings-description" label="Description">
            <Textarea
              id="settings-description"
              rows={3}
              value={general.description}
              onChange={(value) => updateGeneral({ description: value })}
            />
          </FormField>
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Contact</h2>
          <FormField id="settings-email" label="Contact email">
            <TextInput
              id="settings-email"
              type="email"
              value={contact.contact_email}
              onChange={(value) => updateContact({ contact_email: value })}
            />
          </FormField>
          <FormField id="settings-phone" label="Phone">
            <TextInput
              id="settings-phone"
              type="tel"
              value={contact.contact_phone}
              onChange={(value) => updateContact({ contact_phone: value })}
            />
          </FormField>
          <FormField id="settings-whatsapp" label="WhatsApp">
            <TextInput
              id="settings-whatsapp"
              value={contact.whatsapp}
              onChange={(value) => updateContact({ whatsapp: value })}
            />
          </FormField>
          <FormField id="settings-address" label="Address">
            <TextInput
              id="settings-address"
              value={contact.address}
              onChange={(value) => updateContact({ address: value })}
            />
          </FormField>
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Social</h2>
          <p className="admin-section__hint">
            Network key (e.g. <code className="mono">github</code>) and profile URL. Leave the URL empty to remove a key.
          </p>
          {social.length === 0 ? (
            <p className="form-field__hint">No social links configured.</p>
          ) : null}
          <div className="social-rows">
            {social.map((row, index) => (
              <div className="social-row" key={index}>
                <TextInput
                  aria-label={`Social network ${index + 1}`}
                  placeholder="github"
                  value={row.key}
                  onChange={(value) => updateSocial(index, { key: value })}
                  className="social-row__key"
                />
                <TextInput
                  aria-label={`Social URL ${index + 1}`}
                  placeholder="https://github.com/…"
                  type="url"
                  value={row.url}
                  onChange={(value) => updateSocial(index, { url: value })}
                  className="social-row__url"
                />
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => removeSocial(index)}
                  aria-label={`Remove ${row.key || 'social entry'}`}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
          <button type="button" className="btn btn--ghost btn--sm" onClick={addSocial}>
            Add link
          </button>
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Footer</h2>
          <FormField id="settings-copyright" label="Copyright text">
            <TextInput
              id="settings-copyright"
              value={footer.copyright_text}
              onChange={(value) => {
                setFooter({ copyright_text: value })
                markDirty()
              }}
            />
          </FormField>
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">SEO</h2>
          <FormField id="settings-seo-title" label="SEO title">
            <TextInput
              id="settings-seo-title"
              value={seo.seo_title}
              onChange={(value) => updateSeo({ seo_title: value })}
            />
          </FormField>
          <FormField id="settings-seo-description" label="SEO description">
            <Textarea
              id="settings-seo-description"
              rows={3}
              value={seo.seo_description}
              onChange={(value) => updateSeo({ seo_description: value })}
            />
          </FormField>
          <FormField id="settings-seo-keywords" label="SEO keywords" hint="Comma separated">
            <TextInput
              id="settings-seo-keywords"
              value={seo.seo_keywords}
              onChange={(value) => updateSeo({ seo_keywords: value })}
            />
          </FormField>
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Analytics &amp; verification</h2>
          <FormField id="settings-google-verification" label="Google verification" hint="Identifier only — never secrets">
            <TextInput
              id="settings-google-verification"
              value={analytics.google_verification}
              onChange={(value) => updateAnalytics({ google_verification: value })}
            />
          </FormField>
          <FormField id="settings-google-analytics" label="Google Analytics">
            <TextInput
              id="settings-google-analytics"
              value={analytics.google_analytics}
              onChange={(value) => updateAnalytics({ google_analytics: value })}
            />
          </FormField>
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Technical</h2>
          <Toggle
            id="settings-maintenance"
            label="Maintenance mode"
            description="Takes the public site offline behind a maintenance notice. Admins still have full access."
            checked={maintenanceMode}
            onChange={(value) => {
              if (value) {
                setMaintenanceConfirmOpen(true)
              } else {
                setMaintenanceMode(false)
                markDirty()
              }
            }}
          />
        </section>

        {saveError ? (
          <p className="form-field__error form-field__error--form" role="alert">
            {saveError}
          </p>
        ) : null}
        {dirty ? <p className="admin-form__dirty" role="status">Unsaved changes.</p> : null}

        <FormActions onCancel={handleCancel} cancelLabel="Discard">
          <SaveButton busy={saving}>Save settings</SaveButton>
        </FormActions>
      </form>

      <ConfirmDialog
        open={maintenanceConfirmOpen}
        title="Enable maintenance mode?"
        body="The public site will return a maintenance notice until you turn this off. You will still have full admin access."
        confirmLabel="Enable maintenance"
        cancelLabel="Keep site live"
        danger
        onConfirm={() => {
          setMaintenanceMode(true)
          markDirty()
          setMaintenanceConfirmOpen(false)
        }}
        onCancel={() => setMaintenanceConfirmOpen(false)}
      />
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