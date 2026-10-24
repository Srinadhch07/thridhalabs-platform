import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeSanitize from 'rehype-sanitize'
import { getPublicLegal, type LegalPublicItem } from '../../features/legal/api'

export default function LegalPage({ slug, title }: { slug: 'privacy-policy' | 'terms-and-conditions' | 'cookie-policy'; title: string }) {
  const [doc, setDoc] = useState<LegalPublicItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError(false)
    getPublicLegal(slug)
      .then((d) => {
        if (mounted) setDoc(d)
      })
      .catch(() => {
        if (mounted) setError(true)
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [slug])

  return (
    <section className="page-hero">
      <div className="shell">
        <header className="page-hero__header">
          <p className="page-hero__kicker">Legal</p>
          <h1 className="page-hero__title">{doc?.title || title}</h1>
          {(doc?.published_at || doc?.updated_at) && (
            <p className="page-hero__meta">
              {doc?.published_at ? `Published: ${new Date(doc.published_at).toLocaleDateString()}` : `Updated: ${new Date(doc?.updated_at || '').toLocaleDateString()}`}
            </p>
          )}
        </header>
      </div>
      <div className="shell" style={{ paddingBlock: 'clamp(32px, 6vw, 64px)' }}>
        {loading && <p>Loading...</p>}
        {error && <p>This document is not yet published.</p>}
        {!loading && !error && doc && (
          <article className="prose" style={{ maxWidth: '80ch' }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
              {doc.content_markdown}
            </ReactMarkdown>
          </article>
        )}
      </div>
    </section>
  )
}
