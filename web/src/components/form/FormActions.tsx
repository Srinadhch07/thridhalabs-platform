/** Form action row — cancel + primary save. */

import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

export interface FormActionsProps {
  cancelTo?: string
  onCancel?: () => void
  cancelLabel?: string
  children: ReactNode
}

export function FormActions({ cancelTo, onCancel, cancelLabel = 'Cancel', children }: FormActionsProps) {
  return (
    <div className="form-actions">
      {cancelTo ? (
        <Link className="btn btn--ghost" to={cancelTo}>
          {cancelLabel}
        </Link>
      ) : onCancel ? (
        <button type="button" className="btn btn--ghost" onClick={onCancel}>
          {cancelLabel}
        </button>
      ) : null}
      {children}
    </div>
  )
}