/** Neutral placeholder blocks shown while page content loads. */

export function ContentSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="skeleton" aria-hidden="true" data-testid="content-skeleton">
      {Array.from({ length: rows }, (_, index) => (
        <span
          key={index}
          className="skeleton__block"
          style={{ width: `${100 - (index % 3) * 14}%` }}
        />
      ))}
    </div>
  )
}