import { useEffect, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeSanitize from 'rehype-sanitize'
import { getLegal, listLegal, publishLegal, saveLegalDraft, type LegalAdminItem, type LegalSlug } from '../../../features/legal/api'
import { ApiError, getErrorMessage } from '../../../lib/errors/ApiError'
import { usePageMeta } from '../../../lib/utils/seo'
import { PageHeader } from '../../../components/admin/PageHeader'
import { useBeforeUnload } from '../../../lib/hooks/useBeforeUnload'

const SLUGS: Array<{ slug: LegalSlug; label: string }> = [
  { slug: 'privacy-policy', label: 'Privacy Policy' },
  { slug: 'terms-and-conditions', label: 'Terms & Conditions' },
  { slug: 'cookie-policy', label: 'Cookie Policy' },
]

type ViewMode = 'edit' | 'preview' | 'split'

function formatDateTime(value: string | null | undefined): string | null {
  if (!value) return null
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

export default function AdminLegalPagesPage() {
  usePageMeta({ title: 'Legal Pages - Admin - Thridha Labs' })

  const [items, setItems] = useState<LegalAdminItem[]>([])
  const [activeSlug, setActiveSlug] = useState<LegalSlug>('privacy-policy')
  const [doc, setDoc] = useState<LegalAdminItem | null>(null)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [initialTitle, setInitialTitle] = useState('')
  const [initialContent, setInitialContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [loadingList, setLoadingList] = useState(true)
  const [saving, setSaving] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [message, setMessage] = useState<{ tone: 'success' | 'error'; text: string } | null>(null)
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('split')

  const dirty = useMemo(() => {
    if (!doc) return false
    return title !== initialTitle || content !== initialContent
  }, [doc, title, initialTitle, content, initialContent])

  useBeforeUnload(dirty)

  const loadList = async () => {
    setLoadingList(true)
    try {
      const list = await listLegal()
      setItems(list)
    } catch (e) {
      setMessage({ tone: 'error', text: getErrorMessage(e, 'Failed to load legal pages') })
    } finally {
      setLoadingList(false)
    }
  }

  const loadDoc = async (slug: LegalSlug) => {
    setLoading(true)
    setMessage(null)
    try {
      const d = await getLegal(slug)
      setDoc(d)
      setTitle(d.title)
      setContent(d.content_markdown)
      setInitialTitle(d.title)
      setInitialContent(d.content_markdown)
      setLastSavedAt(null)
    } catch (e) {
      setMessage({ tone: 'error', text: getErrorMessage(e, 'Failed to load document') })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadList()
  }, [])

  useEffect(() => {
    void loadDoc(activeSlug)
  }, [activeSlug])

  const handleSlugChange = (slug: LegalSlug) => {
    if (slug === activeSlug) return
    if (dirty) {
      const confirmed = window.confirm('You have unsaved changes. Switch documents without saving?')
      if (!confirmed) return
    }
    setActiveSlug(slug)
  }

  const saveDraft = async () => {
    if (!doc || saving || publishing) return
    setSaving(true)
    setMessage(null)
    try {
      const updated = await saveLegalDraft(activeSlug, {
        title,
        content_markdown: content,
        expected_updated_at: doc.updated_at,
      })
      setDoc(updated)
      setInitialTitle(updated.title)
      setInitialContent(updated.content_markdown)
      setTitle(updated.title)
      setContent(updated.content_markdown)
      setLastSavedAt(new Date().toISOString())
      setMessage({ tone: 'success', text: 'Draft saved' })
      void loadList()
    } catch (e) {
      if (e instanceof ApiError && e.code === 'CONFLICT') {
        setMessage({ tone: 'error', text: 'Conflict: document was modified by another user. Reload and try again.' })
      } else {
        setMessage({ tone: 'error', text: getErrorMessage(e, 'Failed to save draft') })
      }
    } finally {
      setSaving(false)
    }
  }

  const publish = async () => {
    if (!doc || saving || publishing) return
    const confirmed = window.confirm('Publish this legal page? This will make it visible on the public site.')
    if (!confirmed) return
    setPublishing(true)
    setMessage(null)
    try {
      const updated = await publishLegal(activeSlug, {
        title,
        content_markdown: content,
        expected_updated_at: doc.updated_at,
      })
      setDoc(updated)
      setInitialTitle(updated.title)
      setInitialContent(updated.content_markdown)
      setTitle(updated.title)
      setContent(updated.content_markdown)
      setLastSavedAt(null)
      setMessage({ tone: 'success', text: 'Published' })
      void loadList()
    } catch (e) {
      if (e instanceof ApiError && e.code === 'CONFLICT') {
        setMessage({ tone: 'error', text: 'Conflict: document was modified by another user. Reload and try again.' })
      } else {
        setMessage({ tone: 'error', text: getErrorMessage(e, 'Failed to publish') })
      }
    } finally {
      setPublishing(false)
    }
  }

  const status = doc?.status || items.find((i) => i.slug === activeSlug)?.status || 'draft'
  const activeLabel = SLUGS.find((s) => s.slug === activeSlug)?.label || ''
  const publishedAt = formatDateTime(doc?.published_at)
  const updatedAt = formatDateTime(doc?.updated_at)
  const lastSaved = formatDateTime(lastSavedAt)
  const busy = saving || publishing || loading

  return (
    <div className="legal-admin">
      <PageHeader eyebrow="Content" title="Legal Pages" description="Manage and publish legal documents for the public site." />

      <section className="legal-admin__headerbar">
        <div className="legal-admin__docmeta">
          <div className="legal-admin__doctitle-row">
            <h2 className="legal-admin__doctitle">{activeLabel}</h2>
            <span className={status === 'published' ? 'legal-admin__status legal-admin__status--published' : 'legal-admin__status legal-admin__status--draft'}>
              {status === 'published' ? 'Published' : 'Draft'}
            </span>
            {dirty ? <span className="legal-admin__unsaved">Unsaved changes</span> : null}
          </div>
          <div className="legal-admin__metarow">
            {publishedAt ? <span>Last published: {publishedAt}</span> : <span>Not published yet</span>}
            {updatedAt ? <span>Last updated: {updatedAt}</span> : null}
            {lastSaved ? <span>Last saved: {lastSaved}</span> : null}
          </div>
        </div>
        <div className="legal-admin__actions">
          <button type="button" className="btn btn--ghost btn--sm" onClick={saveDraft} disabled={busy || !doc} aria-busy={saving}>
            {saving ? 'Saving...' : 'Save Draft'}
          </button>
          <button type="button" className="btn btn--primary btn--sm" onClick={publish} disabled={busy || !doc} aria-busy={publishing}>
            {publishing ? 'Publishing...' : status === 'published' ? 'Publish Changes' : 'Publish'}
          </button>
        </div>
      </section>

      {message ? (
        <div className={message.tone === 'error' ? 'legal-admin__alert legal-admin__alert--error' : 'legal-admin__alert legal-admin__alert--success'} role="status" aria-live="polite">
          {message.text}
        </div>
      ) : null}

      <div className="legal-admin__layout">
        <aside className="legal-admin__nav" aria-label="Legal documents">
          <p className="legal-admin__nav-title">Documents</p>
          <div className="legal-admin__nav-list">
            {SLUGS.map((s) => {
              const itemStatus = items.find((i) => i.slug === s.slug)?.status || 'draft'
              const isActive = activeSlug === s.slug
              return (
                <button
                  key={s.slug}
                  type="button"
                  className={isActive ? 'legal-admin__nav-item is-active' : 'legal-admin__nav-item'}
                  onClick={() => handleSlugChange(s.slug)}
                  aria-current={isActive ? 'page' : undefined}
                  disabled={busy && isActive}
                >
                  <span className="legal-admin__nav-label">{s.label}</span>
                  <span className={itemStatus === 'published' ? 'legal-admin__nav-status legal-admin__nav-status--published' : 'legal-admin__nav-status legal-admin__nav-status--draft'}>
                    {itemStatus === 'published' ? 'Published' : 'Draft'}
                  </span>
                </button>
              )
            })}
          </div>
          {loadingList ? <p className="legal-admin__nav-hint">Loading status...</p> : null}
        </aside>

        <section className="legal-admin__workspace" aria-label="Legal document editor">
          <div className="legal-admin__workspace-header">
            <div className="legal-admin__title-field">
              <label className="legal-admin__label" htmlFor="legal-title">Page title</label>
              <input id="legal-title" className="legal-admin__input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Page title" disabled={loading} />
            </div>
            <div className="legal-admin__view-toggle" role="group" aria-label="Editor view mode">
              <button type="button" className={viewMode === 'edit' ? 'legal-admin__view-btn is-active' : 'legal-admin__view-btn'} onClick={() => setViewMode('edit')} aria-pressed={viewMode === 'edit'}>Edit</button>
              <button type="button" className={viewMode === 'preview' ? 'legal-admin__view-btn is-active' : 'legal-admin__view-btn'} onClick={() => setViewMode('preview')} aria-pressed={viewMode === 'preview'}>Preview</button>
              <button type="button" className={viewMode === 'split' ? 'legal-admin__view-btn legal-admin__view-btn--split is-active' : 'legal-admin__view-btn legal-admin__view-btn--split'} onClick={() => setViewMode('split')} aria-pressed={viewMode === 'split'}>Split</button>
            </div>
          </div>

          {loading ? (
            <div className="legal-admin__loading">Loading document...</div>
          ) : (
            <div className={'legal-admin__editor-grid legal-admin__editor-grid--' + viewMode}>
              {(viewMode === 'edit' || viewMode === 'split') ? (
                <div className="legal-admin__pane legal-admin__pane--editor">
                  <div className="legal-admin__pane-header">
                    <span className="legal-admin__pane-title">Markdown</span>
                    <span className="legal-admin__pane-hint">Use Markdown for headings, lists, links, and quotes.</span>
                  </div>
                  <textarea className="legal-admin__textarea" value={content} onChange={(e) => setContent(e.target.value)} spellCheck={false} autoCapitalize="off" autoComplete="off" placeholder="# Heading\n\nWrite your legal content in Markdown." aria-label="Legal page markdown content" disabled={loading} />
                </div>
              ) : null}
              {(viewMode === 'preview' || viewMode === 'split') ? (
                <div className="legal-admin__pane legal-admin__pane--preview">
                  <div className="legal-admin__pane-header">
                    <span className="legal-admin__pane-title">Preview</span>
                    <span className="legal-admin__pane-hint">Matches public legal page rendering</span>
                  </div>
                  <div className="legal-admin__preview-surface">
                    <article className="prose legal-admin__prose" style={{ maxWidth: '80ch' }}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
                        {content && content.trim() ? content : '*No content*'}
                      </ReactMarkdown>
                    </article>
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
