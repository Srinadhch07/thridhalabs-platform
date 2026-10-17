/** Admin catch-all — unknown admin section. */

import { Link } from 'react-router-dom'
import { usePageMeta } from '../../lib/utils/seo'

export default function AdminNotFoundPage() {
  usePageMeta({ title: 'Admin section not found — Thridha Labs' })

  return (
    <div className="state-card">
      <p className="eyebrow">404</p>
      <h2 className="state-card__title">Admin section not found</h2>
      <p className="state-card__body">This admin section does not exist.</p>
      <p style={{ marginTop: 'var(--space-5)', marginBottom: 0 }}>
        <Link className="btn btn--ghost" to="/admin">
          Back to dashboard
        </Link>
      </p>
    </div>
  )
}