/** Catch-all placeholder for unpublished admin sections (Phase 7). */

import { usePageMeta } from '../../lib/utils/seo'

export default function AdminPlaceholderPage() {
  usePageMeta({ title: 'Not built yet — Thridha Labs' })

  return (
    <div className="state-card">
      <p className="eyebrow">Admin</p>
      <h2 className="state-card__title">Not built yet</h2>
      <p className="state-card__body">
        This admin section ships with the Phase 7 admin UI.
      </p>
    </div>
  )
}