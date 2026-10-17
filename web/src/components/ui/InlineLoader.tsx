/** Inline (small) loading indicator for in-page actions. */

export function InlineLoader({ label = 'Loading…' }: { label?: string }) {
  return (
    <span className="inline-loader" role="status">
      <span className="spinner spinner--sm" aria-hidden="true" />
      {label}
    </span>
  )
}