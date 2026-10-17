/**
 * Stars — decorative rating with an accessible text equivalent.
 */

export function Stars({ rating, max = 5 }: { rating: number; max?: number }) {
  const clamped = Math.min(Math.max(Math.round(rating), 0), max)
  return (
    <span className="stars" aria-hidden="true" title={`${rating} out of ${max}`}>
      {Array.from({ length: max }, (_, index) => (
        <span key={index}>{index < clamped ? '◆' : '◇'}</span>
      ))}
    </span>
  )
}

/** Accessible companion for screen readers. */
export function StarLabel({ rating, max = 5 }: { rating: number; max?: number }) {
  return (
    <span className="visually-hidden">
      Rated {rating} out of {max}
    </span>
  )
}