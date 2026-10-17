/**
 * ErrorState — generic, user-safe error display.
 *
 * Never renders raw error objects or stack traces; only safe messages.
 */

import { getErrorMessage } from '../../lib/errors/ApiError'

export interface ErrorStateProps {
  title?: string
  /** Raw error (e.g. from a hook/catch) — sanitized before display. */
  error?: unknown
  /** An already-safe display message (used when no `error` object is given). */
  message?: string
  onRetry?: () => void
  retryLabel?: string
}

export function ErrorState({
  title = 'Something went wrong',
  error,
  message,
  onRetry,
  retryLabel = 'Try again',
}: ErrorStateProps) {
  const safeMessage = error !== undefined ? getErrorMessage(error) : (message ?? 'Please try again later.')
  return (
    <div className="state-card state-card--error" role="alert">
      <p className="eyebrow">Error</p>
      <h2 className="state-card__title">{title}</h2>
      <p className="state-card__body">{safeMessage}</p>
      {onRetry && (
        <button type="button" className="btn btn--ghost" onClick={onRetry}>
          {retryLabel}
        </button>
      )}
    </div>
  )
}