/** 403 — forbidden state. */

export function ForbiddenState() {
  return (
    <div className="state-card" role="alert">
      <p className="eyebrow">403</p>
      <h2 className="state-card__title">Access denied</h2>
      <p className="state-card__body">You do not have permission to view this content.</p>
    </div>
  )
}