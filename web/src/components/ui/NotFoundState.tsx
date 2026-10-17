/** 404 — page not found state. */

import { Link } from 'react-router-dom'

export function NotFoundState({ title = 'Page not found' }: { title?: string }) {
  return (
    <div className="state-card" role="alert">
      <p className="eyebrow">404</p>
      <h2 className="state-card__title">{title}</h2>
      <p className="state-card__body">The page you are looking for does not exist or has moved.</p>
      <Link className="btn btn--ghost" to="/">
        Back to home
      </Link>
    </div>
  )
}