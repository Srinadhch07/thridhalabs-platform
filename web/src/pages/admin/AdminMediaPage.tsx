/**
 * Admin media library — upload, browse, preview metadata and delete.
 * Deleting is admin+ in the backend, so editors see it disabled.
 */

import { useRef, useState } from 'react'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage, isApiError } from '../../lib/errors/ApiError'
import { useMediaList } from '../../features/media/hooks'
import { deleteMedia, uploadMedia } from '../../features/media/api'
import { useAuth } from '../../app/providers/AuthProvider'
import { canDelete } from '../../features/auth/rbac'
import { resolveMediaUrl } from '../../lib/utils/mediaUrl'
import { PageHeader } from '../../components/admin/PageHeader'
import { Pagination } from '../../components/admin/Pagination'
import { ConfirmDialog } from '../../components/form/ConfirmDialog'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { EmptyState } from '../../components/ui/EmptyState'
import type { Media } from '../../types/media'

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function AdminMediaPage() {
  usePageMeta({ title: 'Media — Admin — Thridha Labs' })

  const { user } = useAuth()
  const mayDelete = canDelete(user?.role)
  const [page, setPage] = useState(1)
  const { data, loading, error, reload } = useMediaList({ page, page_size: 24, sort: 'newest' })
  useAdminSessionIssue(error)

  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Media | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFiles(files: FileList | null): Promise<void> {
    const file = files?.[0]
    if (!file) return
    setUploading(true)
    setUploadError(null)
    try {
      await uploadMedia(file)
      if (inputRef.current) inputRef.current.value = ''
      await reload()
    } catch (caught) {
      if (isApiError(caught) && caught.status === 413) {
        setUploadError('That file is too large. The upload limit is enforced by the server.')
      } else if (isApiError(caught) && caught.status === 415) {
        setUploadError('Unsupported format. Only JPEG, PNG and WebP images are accepted.')
      } else {
        setUploadError(getErrorMessage(caught, 'Could not upload the file.'))
      }
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete(): Promise<void> {
    if (!selected) return
    setDeleting(true)
    setActionError(null)
    try {
      await deleteMedia(selected.id)
      setDeleteOpen(false)
      setSelected(null)
      await reload()
    } catch (caught) {
      setActionError(getErrorMessage(caught, 'Could not delete the media.'))
    } finally {
      setDeleting(false)
    }
  }

  const items = data?.items ?? []

  return (
    <div>
      <PageHeader
        eyebrow="Library"
        title="Media"
        description="Upload and manage images used across the site."
      />

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="visually-hidden"
        data-testid="media-upload-input"
        onChange={(event) => void handleFiles(event.target.files)}
      />
      <div className="admin-upload">
        {uploading ? (
          <span className="inline-loader" role="status">Uploading…</span>
        ) : (
          <button type="button" className="btn btn--primary" onClick={() => inputRef.current?.click()}>
            Choose image…
          </button>
        )}
        <span className="admin-upload__hint">JPEG, PNG or WebP — server-validated.</span>
        {uploadError ? (
          <p className="form-field__error" role="alert">
            {uploadError}
          </p>
        ) : null}
      </div>

      {loading ? <ContentSkeleton rows={4} /> : null}
      {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}
      {!loading && !error && items.length === 0 ? (
        <EmptyState title="No media yet" description="Upload your first image to use it in branding, clients, projects and more." />
      ) : null}

      {items.length > 0 ? (
        <>
          <div className="admin-media-grid">
            {items.map((item) => {
              const url = resolveMediaUrl(item, 'thumb') ?? resolveMediaUrl(item)
              return (
                <button
                  key={item.id}
                  type="button"
                  className="admin-media-tile"
                  onClick={() => setSelected(item)}
                  title={item.original_name}
                >
                  {url ? (
                    <img src={url} alt={item.original_name} loading="lazy" className="admin-media-tile__img" />
                  ) : (
                    <span className="admin-media-tile__img admin-media-tile__img--placeholder" aria-hidden="true" />
                  )}
                  <span className="admin-media-tile__name">{item.original_name}</span>
                  <span className="admin-media-tile__meta">
                    {item.width}×{item.height} · {formatBytes(item.size_bytes)}
                  </span>
                </button>
              )
            })}
          </div>
          <Pagination page={data?.page ?? 1} pages={data?.pages ?? 1} total={data?.total ?? 0} onChange={setPage} />
        </>
      ) : null}

      <ConfirmDialog
        open={deleteOpen}
        title="Delete this media?"
        body={
          selected
            ? `"${selected.original_name}" and all of its served variants will be permanently removed. Content referencing it may break.`
            : 'This media will be permanently removed.'
        }
        confirmLabel="Delete"
        cancelLabel="Cancel"
        danger
        busy={deleting}
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeleteOpen(false)}
      />

      {selected ? (
        <div
          className="dialog-backdrop"
          onMouseDown={(e) => e.target === e.currentTarget && setSelected(null)}
        >
          <div role="dialog" aria-modal="true" aria-labelledby="media-preview-title" className="dialog dialog--wide">
            <div className="dialog__header">
              <h2 id="media-preview-title" className="dialog__title">
                {selected.original_name}
              </h2>
              <button type="button" className="btn btn--ghost btn--sm" onClick={() => setSelected(null)}>
                Close
              </button>
            </div>
            <div className="media-preview">
              <div className="media-preview__img-wrap">
                {(() => {
                  const url = resolveMediaUrl(selected, 'md') ?? resolveMediaUrl(selected)
                  return url ? <img src={url} alt={selected.original_name} className="media-preview__img" /> : null
                })()}
              </div>
              <dl className="media-preview__meta">
                <div>
                  <dt>Format</dt>
                  <dd className="mono">{selected.format}</dd>
                </div>
                <div>
                  <dt>Dimensions</dt>
                  <dd>
                    {selected.width}×{selected.height}
                  </dd>
                </div>
                <div>
                  <dt>Size</dt>
                  <dd>{formatBytes(selected.size_bytes)}</dd>
                </div>
                <div>
                  <dt>MIME</dt>
                  <dd className="mono">{selected.mime_type}</dd>
                </div>
                <div>
                  <dt>Checksum</dt>
                  <dd className="mono">{selected.checksum.slice(0, 16)}…</dd>
                </div>
                <div>
                  <dt>Storage</dt>
                  <dd className="mono">{selected.storage_mode}</dd>
                </div>
                <div>
                  <dt>Variants</dt>
                  <dd>
                    {selected.variants.map((variant) => `${variant.name} (${variant.width}×${variant.height})`).join(', ')}
                  </dd>
                </div>
              </dl>
            </div>
            {actionError ? (
              <p className="form-field__error" role="alert">
                {actionError}
              </p>
            ) : null}
            <div className="dialog__actions">
              {mayDelete ? (
                <button type="button" className="btn btn--danger" onClick={() => setDeleteOpen(true)}>
                  Delete
                </button>
              ) : (
                <p className="media-preview__rbac-note">
                  Deleting requires an admin or owner account.
                </p>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}