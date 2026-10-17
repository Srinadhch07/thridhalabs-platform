/** Maintenance page — rendered by the layout when maintenance mode is on. */

import { usePageMeta } from '../../lib/utils/seo'

export default function MaintenancePage() {
  usePageMeta({ title: 'Maintenance — Thridha Labs', robots: 'noindex, nofollow' })

  return (
    <div className="shell" style={{ paddingBlock: 'calc(var(--space-8) + 48px)' }}>
      <div className="state-card">
        <p className="eyebrow">
          <span className="hud-dot" aria-hidden="true" /> Thridha Labs / system status
        </p>
        <h2 className="state-card__title">Brief maintenance in progress</h2>
        <p className="state-card__body">
          The lab is undergoing scheduled maintenance. Please check back shortly.
        </p>
      </div>
    </div>
  )
}