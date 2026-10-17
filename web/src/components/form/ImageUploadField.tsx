/**
 * ImageUploadField — contextual single-image upload for admin and member forms.
 *
 * Uploads directly through the media API and hands the resulting media id to the
 * owning form field. It deliberately never browses or fetches the media library:
 * only the currently selected image is loaded for its preview.
 *
 * - Replace: a new upload changes the field only after it succeeds; a failed
 *   upload leaves the previous selection untouched.
 * - Remove: clears the field reference only — the underlying media asset is
 *   never deleted (asset lifecycle stays in the Media library).
 *
 * `ImageGalleryField` reuses the same building blocks for ordered multi-image
 * fields (work galleries, block image galleries).
 */

import { useEffect, useRef, useState } from 'react'
import { resolveMediaUrl } from '../../lib/utils/mediaUrl'
import { getErrorMessage, isApiError } from '../../lib/errors/ApiError'
import type { Media } from '../../types/media'

/** Accepted image MIME types (kept in sync with the backend allow-list). */
export const IMAGE_ACCEPT = 'image/png,image/jpeg,image/webp'
export const IMAGE_FORMAT_HINT = 'PNG, JPEG or WebP'
/** Client-side pre-check mirroring the default PRODUCT_IMAGE_MAX_BYTES (5 MiB). */
export const IMAGE_MAX_BYTES = 5 * 1024 * 1024
export const IMAGE_SIZE_HINT = 'up to 5 MB'

/** Return a user-facing validation problem for a chosen file, or null when OK. */
export function validateImageFile(file: File): string | null {
  if (!file.type.startsWith('image/')) {
    return `Unsupported file. Choose a ${IMAGE_FORMAT_HINT} image.`
  }
  if (file.size > IMAGE_MAX_BYTES) {
    return `That image is too large. The limit is ${IMAGE_SIZE_HINT}.`
  }
  return null
}

/** Map an upload failure to a safe, user-facing message. */
export function imageUploadErrorMessage(caught: unknown): string {
  if (isApiError(caught) && caught.status === 413) {
    return `That image is too large. The limit is ${IMAGE_SIZE_HINT}.`
  }
  if (isApiError(caught) && caught.status === 415) {
    return `Unsupported format. Choose a ${IMAGE_FORMAT_HINT} image.`
  }
  if (isApiError(caught) && caught.status === 422) {
    return 'That image could not be processed. Try a different file.'
  }
  return getErrorMessage(caught, 'Could not upload the image.')
}

export interface ImageUploadFieldProps {
  id: string
  label: string
  value: string | null
  onChange: (mediaId: string | null) => void
  /** Upload implementation (admin library vs member-scoped). */
  upload: (file: File) => Promise<Media>
  /**
   * Resolve a preview URL for an existing media reference. Admin forms pass an
   * authenticated lookup; member forms omit it and fall back to the public
   * delivery route (which needs no session).
   */
  resolvePreviewUrl?: (mediaId: string) => Promise<string | null>
  /** Media variant used for the preview (defaults to `thumb`). */
  variant?: string
  allowRemove?: boolean
  disabled?: boolean
  aspectRatio?: string
  hint?: string
  /** Show the format/size requirements line (hidden when a gallery shows it). */
  showRequirements?: boolean
  className?: string
}

export function ImageUploadField({
  id,
  label,
  value,
  onChange,
  upload,
  resolvePreviewUrl,
  variant = 'thumb',
  allowRemove = true,
  disabled = false,
  aspectRatio,
  hint,
  showRequirements = true,
  className = '',
}: ImageUploadFieldProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const resolvedId = useRef<string | null>(null)
  const busy = uploading

  // Load a preview whenever the referenced media id changes (hydration or an
  // external update). Uploads set the preview directly and are skipped here.
  useEffect(() => {
    if (!value) {
      resolvedId.current = null
      setPreviewUrl(null)
      setPreviewLoading(false)
      return
    }
    if (resolvedId.current === value) return
    resolvedId.current = value
    if (!resolvePreviewUrl) {
      setPreviewUrl(resolveMediaUrl(value, variant))
      return
    }
    let cancelled = false
    setPreviewLoading(true)
    resolvePreviewUrl(value)
      .then((url) => {
        if (!cancelled) setPreviewUrl(url)
      })
      .catch(() => {
        if (!cancelled) setPreviewUrl(null)
      })
      .finally(() => {
        if (!cancelled) setPreviewLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [value, resolvePreviewUrl, variant])

  async function handleFile(file: File | undefined): Promise<void> {
    if (!file) return
    setError(null)
    const problem = validateImageFile(file)
    if (problem) {
      setError(problem)
      return
    }
    setUploading(true)
    try {
      const media = await upload(file)
      resolvedId.current = media.id
      setPreviewUrl(resolveMediaUrl(media, variant) ?? resolveMediaUrl(media))
      setPreviewLoading(false)
      onChange(media.id)
    } catch (caught) {
      setError(imageUploadErrorMessage(caught))
    } finally {
      setUploading(false)
    }
  }

  function remove(): void {
    setError(null)
    resolvedId.current = null
    setPreviewUrl(null)
    onChange(null)
  }

  const hasImage = Boolean(value)
  // The fixed ratio frames the *empty* placeholder only. Once an image exists
  // the preview sizes to the image (see `.image-upload--framed`), so the admin
  // sees the entire banner exactly as the public site shows it — no crop.
  const previewStyle = aspectRatio ? { aspectRatio } : undefined
  const framedClass = aspectRatio ? ' image-upload--framed' : ''

  return (
    <div
      className={`image-upload${framedClass}${className ? ` ${className}` : ''}`}
      aria-busy={busy || previewLoading}
    >
      <div className="image-upload__header">
        <label className="image-upload__label" htmlFor={id}>
          {label}
        </label>
        {hasImage && allowRemove ? (
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            disabled={disabled || busy}
            onClick={remove}
          >
            Remove
          </button>
        ) : null}
      </div>

      <input
        ref={fileRef}
        id={id}
        type="file"
        accept={IMAGE_ACCEPT}
        className="visually-hidden"
        disabled={disabled || busy}
        data-testid={`${id}-input`}
        onChange={(event) => {
          const file = event.target.files?.[0]
          event.target.value = ''
          void handleFile(file)
        }}
      />

      {hasImage ? (
        <div className="image-upload__preview">
          {previewLoading && !previewUrl ? (
            <span className="image-upload__placeholder" role="status">
              <span className="spinner spinner--sm" aria-hidden="true" /> Loading…
            </span>
          ) : previewUrl ? (
            <img className="image-upload__img" src={previewUrl} alt={label} />
          ) : (
            <span className="image-upload__placeholder">Preview unavailable</span>
          )}
        </div>
      ) : (
        <div className="image-upload__empty" style={previewStyle}>
          <span className="image-upload__empty-icon" aria-hidden="true">
            +
          </span>
          <span className="image-upload__empty-text">No image selected</span>
        </div>
      )}

      <div className="image-upload__actions">
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          disabled={disabled || busy}
          onClick={() => fileRef.current?.click()}
        >
          {busy ? 'Uploading…' : hasImage ? 'Replace image' : 'Upload image'}
        </button>
        {busy ? <progress className="image-upload__progress" aria-label="Uploading image" /> : null}
      </div>

      {showRequirements ? (
        <p className="image-upload__hint">
          {hint ? `${hint} · ` : ''}
          {IMAGE_FORMAT_HINT} · {IMAGE_SIZE_HINT}
        </p>
      ) : hint ? (
        <p className="image-upload__hint">{hint}</p>
      ) : null}

      {error ? (
        <p className="form-field__error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}

export interface ImageGalleryFieldProps {
  id: string
  label: string
  value: string[]
  onChange: (mediaIds: string[]) => void
  upload: (file: File) => Promise<Media>
  resolvePreviewUrl?: (mediaId: string) => Promise<string | null>
  variant?: string
  disabled?: boolean
  hint?: string
  className?: string
}

export function ImageGalleryField({
  id,
  label,
  value,
  onChange,
  upload,
  resolvePreviewUrl,
  variant = 'thumb',
  disabled = false,
  hint,
  className = '',
}: ImageGalleryFieldProps) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleFile(file: File | undefined): Promise<void> {
    if (!file) return
    setError(null)
    const problem = validateImageFile(file)
    if (problem) {
      setError(problem)
      return
    }
    setBusy(true)
    try {
      const media = await upload(file)
      onChange([...value, media.id])
    } catch (caught) {
      setError(imageUploadErrorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className={`image-gallery${className ? ` ${className}` : ''}`} aria-busy={busy}>
      <div className="image-upload__header">
        <span className="image-upload__label">
          {label}
          {value.length > 0 ? ` · ${value.length}` : ''}
        </span>
      </div>

      <input
        ref={fileRef}
        id={id}
        type="file"
        accept={IMAGE_ACCEPT}
        className="visually-hidden"
        disabled={disabled || busy}
        data-testid={`${id}-input`}
        onChange={(event) => {
          const file = event.target.files?.[0]
          event.target.value = ''
          void handleFile(file)
        }}
      />

      {value.length === 0 ? (
        <p className="image-upload__empty-text">No images yet.</p>
      ) : (
        <div className="image-gallery__grid">
          {value.map((mediaId, index) => (
            <div className="image-gallery__item" key={`${mediaId}-${index}`}>
              <ImageUploadField
                id={`${id}-${index}`}
                label={`Image ${index + 1}`}
                value={mediaId}
                onChange={(nextId) => {
                  if (nextId) {
                    onChange(value.map((existing, i) => (i === index ? nextId : existing)))
                  } else {
                    onChange(value.filter((_, i) => i !== index))
                  }
                }}
                upload={upload}
                resolvePreviewUrl={resolvePreviewUrl}
                variant={variant}
                disabled={disabled || busy}
                allowRemove={false}
                showRequirements={false}
              />
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                disabled={disabled || busy}
                onClick={() => onChange(value.filter((_, i) => i !== index))}
                aria-label={`Remove image ${index + 1}`}
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="image-upload__actions">
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          disabled={disabled || busy}
          onClick={() => fileRef.current?.click()}
        >
          {busy ? 'Uploading…' : 'Add image'}
        </button>
        {busy ? <progress className="image-upload__progress" aria-label="Uploading image" /> : null}
      </div>

      <p className="image-upload__hint">
        {hint ? `${hint} · ` : ''}
        {IMAGE_FORMAT_HINT} · {IMAGE_SIZE_HINT}
      </p>

      {error ? (
        <p className="form-field__error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}
