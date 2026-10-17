/**
 * MemberEmptyState — friendly placeholder for member views without content.
 */

import type { ReactNode } from 'react'

interface MemberEmptyStateProps {
  title?: string
  description?: string
  action?: ReactNode
}

export function MemberEmptyState({
  title = 'Nothing here yet',
  description,
  action,
}: MemberEmptyStateProps) {
  return (
    <div className="member-empty">
      <p className="member-empty__title">{title}</p>
      {description ? <p className="member-empty__body">{description}</p> : null}
      {action}
    </div>
  )
}
