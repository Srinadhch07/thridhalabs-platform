/** Full-page loading state. */

export function PageLoader({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="loader" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span className="loader__label">{label}</span>
    </div>
  )
}