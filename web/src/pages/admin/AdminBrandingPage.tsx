/**
 * Admin branding — theme presets, colors, theme mode and media references,
 * with a live preview and a reset-to-default action (guarded by confirmation).
 */

import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { useBeforeUnload } from '../../lib/hooks/useBeforeUnload'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { useAdminBranding } from '../../features/branding/hooks'
import { updateBranding } from '../../features/branding/api'
import { resolveAdminMediaPreviewUrl, uploadMedia } from '../../features/media/api'
import {
  BRANDING_PRESETS,
  findBrandingPreset,
  getBrandingPreset,
  presetColorsEqual,
} from '../../lib/utils/brandingPresets'
import { PageHeader } from '../../components/admin/PageHeader'
import { FormField } from '../../components/form/FormField'
import { ColorInput } from '../../components/form/ColorInput'
import { Select } from '../../components/form/Select'
import { ImageUploadField } from '../../components/form/ImageUploadField'
import { FormActions } from '../../components/form/FormActions'
import { SaveButton } from '../../components/form/SaveButton'
import { ConfirmDialog } from '../../components/form/ConfirmDialog'
import { ThemePresetCard } from '../../components/branding/ThemePresetCard'
import { BrandingPreview } from '../../components/branding/BrandingPreview'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import type { BrandingColors, BrandingMediaRefs, BrandingMode } from '../../types/branding'

const DEFAULT_COLORS: BrandingColors = {
  primary: '#4f46e5',
  secondary: '#0ea5e9',
  accent: '#f59e0b',
  background: '#ffffff',
  text: '#0f172a',
}

const DEFAULT_MEDIA: BrandingMediaRefs = {
  logo: null,
  logo_dark: null,
  logo_light: null,
  favicon: null,
  og_image: null,
}

const MEDIA_FIELDS: { key: keyof BrandingMediaRefs; label: string }[] = [
  { key: 'logo', label: 'Logo (light backgrounds)' },
  { key: 'logo_dark', label: 'Logo (dark backgrounds)' },
  { key: 'logo_light', label: 'Logo (light backgrounds, alt)' },
  { key: 'favicon', label: 'Favicon' },
  { key: 'og_image', label: 'Social share image (Open Graph)' },
]

const COLOR_FIELDS: { key: keyof BrandingColors; label: string }[] = [
  { key: 'primary', label: 'Primary' },
  { key: 'secondary', label: 'Secondary' },
  { key: 'accent', label: 'Accent' },
  { key: 'background', label: 'Background' },
  { key: 'text', label: 'Text' },
]

export default function AdminBrandingPage() {
  usePageMeta({ title: 'Branding — Admin — Thridha Labs' })

  const { data, loading, error, reload } = useAdminBranding()
  useAdminSessionIssue(error)

  const navigate = useNavigate()

  const [colors, setColors] = useState<BrandingColors>(DEFAULT_COLORS)
  const [mode, setMode] = useState<BrandingMode>('light')
  const [media, setMedia] = useState<BrandingMediaRefs>(DEFAULT_MEDIA)
  const [themePreset, setThemePreset] = useState<string | null>(null)

  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  useBeforeUnload(dirty)
  const [resetOpen, setResetOpen] = useState(false)
  const [discardOpen, setDiscardOpen] = useState(false)

  const hydrated = useRef(false)
  useEffect(() => {
    if (!data || hydrated.current) return
    hydrated.current = true
    setColors(data.colors)
    setMode(data.mode)
    setMedia(data.media)
    const preset = getBrandingPreset(data.theme_preset)
    const matches = preset !== null && preset.mode === data.mode && presetColorsEqual(preset.colors, data.colors)
    setThemePreset(matches ? data.theme_preset : null)
    setDirty(false)
  }, [data])

  function markDirty(): void {
    setDirty(true)
  }

  function handlePresetSelect(presetId: string): void {
    const preset = getBrandingPreset(presetId)
    if (!preset) return
    setColors(preset.colors)
    setMode(preset.mode)
    setThemePreset(preset.id)
    markDirty()
  }

  function handleColorChange(key: keyof BrandingColors, value: string): void {
    setColors((prev) => ({ ...prev, [key]: value }))
    setThemePreset(null) // any customization makes the palette custom
    markDirty()
  }

  function handleModeChange(value: string): void {
    setMode(value as BrandingMode)
    setThemePreset(null)
    markDirty()
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    setSaving(true)
    setSaveError(null)
    try {
      await updateBranding({ colors, mode, media, theme_preset: themePreset })
      await reload()
      setDirty(false)
    } catch (caught) {
      setSaveError(getErrorMessage(caught, 'Could not save branding.'))
    } finally {
      setSaving(false)
    }
  }

  function handleReset(): void {
    setColors(DEFAULT_COLORS)
    setMode('light')
    setMedia(DEFAULT_MEDIA)
    setThemePreset(null)
    setDirty(true)
    setResetOpen(false)
  }

  function handleCancel(): void {
    if (dirty) {
      setDiscardOpen(true)
    } else {
      navigate('/admin')
    }
  }

  const activePreset = findBrandingPreset(colors, mode)
  const isCustom = activePreset === null

  if (loading || !data) {
    return <ContentSkeleton rows={4} />
  }

  if (error) {
    return <ErrorState error={error} onRetry={reload} />
  }

  return (
    <div>
      <PageHeader
        eyebrow="Appearance"
        title="Branding"
        description="Colors, theme mode and brand media. Saved instantly to the live site."
      />

      <form className="admin-form" onSubmit={handleSubmit} noValidate>
        <section className="admin-section">
          <div className="admin-section__head">
            <h2 className="admin-section__title">Color themes</h2>
            {isCustom ? <span className="theme-status theme-status--custom">Custom</span> : null}
          </div>
          <p className="admin-section__hint">
            Choose a theme as your starting point. Customize any color afterward to make it yours.
          </p>
          <div className="theme-grid">
            {BRANDING_PRESETS.map((preset) => (
              <ThemePresetCard
                key={preset.id}
                preset={preset}
                groupName="branding-theme"
                selected={activePreset?.id === preset.id}
                onSelect={handlePresetSelect}
              />
            ))}
          </div>
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Colors</h2>
          <div className="color-grid">
            {COLOR_FIELDS.map((field) => (
              <FormField key={field.key} id={`branding-${field.key}`} label={field.label}>
                <ColorInput
                  id={`branding-${field.key}`}
                  label={field.label}
                  value={colors[field.key]}
                  onChange={(value) => handleColorChange(field.key, value)}
                />
              </FormField>
            ))}
          </div>
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Theme</h2>
          <FormField id="branding-mode" label="Default theme">
            <Select
              id="branding-mode"
              options={[
                { value: 'light', label: 'Light' },
                { value: 'dark', label: 'Dark' },
              ]}
              value={mode}
              onChange={handleModeChange}
            />
          </FormField>
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Media</h2>
          {MEDIA_FIELDS.map((field) => (
            <ImageUploadField
              key={field.key}
              id={`branding-${field.key}`}
              label={field.label}
              value={media[field.key]}
              onChange={(mediaId) => {
                setMedia((prev) => ({ ...prev, [field.key]: mediaId }))
                markDirty()
              }}
              upload={uploadMedia}
              resolvePreviewUrl={resolveAdminMediaPreviewUrl}
              className="admin-section__field"
            />
          ))}
        </section>

        <section className="admin-section">
          <h2 className="admin-section__title">Preview</h2>
          <BrandingPreview colors={colors} mode={mode} />
          <div className="admin-section__actions">
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => setResetOpen(true)}
              aria-label="Reset branding to defaults"
            >
              Reset to defaults
            </button>
          </div>
        </section>

        {saveError ? (
          <p className="form-field__error form-field__error--form" role="alert">
            {saveError}
          </p>
        ) : null}
        {dirty ? <p className="admin-form__dirty" role="status">Unsaved changes.</p> : null}

        <FormActions onCancel={handleCancel} cancelLabel="Discard">
          <SaveButton busy={saving}>Save branding</SaveButton>
        </FormActions>
      </form>

      <ConfirmDialog
        open={resetOpen}
        title="Reset branding?"
        body="This restores the default colors, clears the selected theme and media references. You still need to save to apply it."
        confirmLabel="Reset"
        cancelLabel="Cancel"
        danger
        onConfirm={handleReset}
        onCancel={() => setResetOpen(false)}
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