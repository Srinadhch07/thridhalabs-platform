import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeSanitize from 'rehype-sanitize'
import { getLegal, listLegal, publishLegal, saveLegalDraft, type LegalAdminItem, type LegalSlug } from '../../../features/legal/api'
import { ApiError } from '../../../lib/errors/ApiError'

const SLUGS: Array<{ slug: LegalSlug; label: string }> = [
  { slug: 'privacy-policy', label: 'Privacy Policy' },
  { slug: 'terms-and-conditions', label: 'Terms & Conditions' },
  { slug: 'cookie-policy', label: 'Cookie Policy' },
]

export default function AdminLegalPagesPage() {
  const [items, setItems] = useState<LegalAdminItem[]>([])
  const [activeSlug, setActiveSlug] = useState<LegalSlug>('privacy-policy')
  const [doc, setDoc] = useState<LegalAdminItem | null>(null)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [message, setMessage] = useState<{ tone: 'success' | 'error'; text: string } | null>(null)

  const loadList = async () => {
    try {
      const list = await listLegal()
      setItems(list)
    } catch (e) {
      setMessage({ tone: 'error', text: e instanceof ApiError ? e.message : 'Failed to load legal pages' })
    }
  }

  const loadDoc = async (slug: LegalSlug) => {
    setLoading(true)
    try {
      const d = await getLegal(slug)
      setDoc(d)
      setTitle(d.title)
      setContent(d.content_markdown)
    } catch (e) {
      setMessage({ tone: 'error', text: e instanceof ApiError ? e.message : 'Failed to load document' })
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

  const saveDraft = async () => {
    if (!doc) return
    setSaving(true)
    setMessage(null)
    try {
      const updated = await saveLegalDraft(activeSlug, {
        title,
        content_markdown: content,
        expected_updated_at: doc.updated_at,
      })
      setDoc(updated)
      setMessage({ tone: 'success', text: 'Draft saved' })
      void loadList()
    } catch (e) {
      if (e instanceof ApiError && e.code === 'CONFLICT') {
        setMessage({ tone: 'error', text: 'Conflict: document was modified by another user. Reload and try again.' })
      } else {
        setMessage({ tone: 'error', text: e instanceof ApiError ? e.message : 'Failed to save draft' })
      }
    } finally {
      setSaving(false)
    }
  }

  const publish = async () => {
    if (!doc) return
    if (!confirm('Publish this legal page? This will make it visible on the public site.')) return
    setPublishing(true)
    setMessage(null)
    try {
      const updated = await publishLegal(activeSlug, {
        title,
        content_markdown: content,
        expected_updated_at: doc.updated_at,
      })
      setDoc(updated)
      setMessage({ tone: 'success', text: 'Published' })
      void loadList()
    } catch (e) {
      if (e instanceof ApiError && e.code === 'CONFLICT') {
        setMessage({ tone: 'error', text: 'Conflict: document was modified by another user. Reload and try again.' })
      } else {
        setMessage({ tone: 'error', text: e instanceof ApiError ? e.message : 'Failed to publish' })
      }
    } finally {
      setPublishing(false)
    }
  }

  const status = doc?.status || items.find((i) => i.slug === activeSlug)?.status || 'draft'

  return (
    <section className="admin-page">
      <header className="admin-page__header">
        <div>
          <h1 className="admin-page__title">Legal Pages</h1>
          <p className="admin-page__subtitle">Manage Privacy Policy, Terms & Conditions, and Cookie Policy</p>
        </div>
      </header>

      <div className="admin-card" style={{ marginBottom: 16 }}>
        <div className="admin-card__body" style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {SLUGS.map((s) => (
            <button
              key={s.slug}
              type="button"
              className={`admin-btn ${activeSlug === s.slug ? 'admin-btn--primary' : 'admin-btn--ghost'}`}
              onClick={() => setActiveSlug(s.slug)}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {message && (
        <div className={`admin-card`} style={{ marginBottom: 16, borderColor: message.tone === 'error' ? 'var(--err)' : 'var(--ok)' }}>
          <div className="admin-card__body">
            <span>{message.text}</span>
          </div>
        </div>
      )}
      <div className="admin-card">
        <div className="admin-card__header">
          <div>
            <h2 className="admin-card__title">{SLUGS.find((s) => s.slug === activeSlug)?.label}</h2>
            <p className="admin-card__subtitle">
              Status: {status} {doc?.published_at ? `| Published: ${new Date(doc.published_at).toLocaleString()}` : ''} {doc?.updated_at ? `| Updated: ${new Date(doc.updated_at).toLocaleString()}` : ''}
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" className="admin-btn admin-btn--ghost" onClick={saveDraft} disabled={saving || loading}>
              {saving ? 'Saving...' : 'Save Draft'}
            </button>
            <button type="button" className="admin-btn admin-btn--primary" onClick={publish} disabled={publishing || loading}>
              {publishing ? 'Publishing...' : 'Publish'}
            </button>
          </div>
        </div>
        <div className="admin-card__body" style={{ display: 'grid', gap: 16 }}>
          <div>
            <label className="admin-label">Title</label>
            <input className="admin-input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Page title" />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <label className="admin-label">Markdown</label>
              <textarea
                className="admin-textarea"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={24}
                style={{ width: '100%', fontFamily: 'monospace', fontSize: 13 }}
              />
            </div>
            <div>
              <label className="admin-label">Preview</label>
              <div className="admin-card" style={{ height: '100%', overflow: 'auto' }}>
                <div className="admin-card__body prose" style={{ maxWidth: 'none' }}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
                    {content || '*No content*'}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
