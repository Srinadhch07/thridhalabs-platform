/** Full-page loading state. */

export function PageLoader({ label = 'Booting the lab' }: { label?: string }) {
  return (
    <div className="lab-boot" role="status" aria-live="polite">
      <div className="lab-boot__inner">
        <div className="lab-boot__header">
          <span className="lab-boot__mark">THRIDHA LABS</span>
          <span className="lab-boot__status">BOOTING</span>
        </div>
        <div className="lab-boot__body">
          <div className="lab-boot__progress" aria-hidden="true">
            <div className="lab-boot__progress-bar" />
          </div>
          <div className="lab-boot__meta">
            <span className="lab-boot__label">{label}</span>
            <span className="lab-boot__dots" aria-hidden="true" />
          </div>
        </div>
      </div>
    </div>
  )
}