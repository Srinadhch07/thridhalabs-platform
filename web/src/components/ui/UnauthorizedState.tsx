/** 401 — authentication required state. */

export function UnauthorizedState() {
  return (
    <div className="state-card" role="alert">
      <p className="eyebrow">401</p>
      <h2 className="state-card__title">Sign in required</h2>
      <p className="state-card__body">You need to sign in to view this content.</p>
    </div>
  )
}