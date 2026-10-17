/**
 * MemberCard — bordered content panel with an optional title/description
 * header. Uses a member-namespaced class so the public and admin card styles
 * stay independent.
 */

import type { ReactNode } from 'react'

interface MemberCardProps {
  title?: string
  description?: string
  action?: ReactNode
  interactive?: boolean
  flush?: boolean
  className?: string
  children: ReactNode
}

export function MemberCard({
  title,
  description,
  action,
  interactive,
  flush,
  className = '',
  children,
}: MemberCardProps) {
  const classes = [
    'member-card',
    interactive ? 'member-card--interactive' : '',
    flush ? 'member-card--flush' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  const hasHeader = title || description || action

  return (
    <section className={classes}>
      {hasHeader ? (
        <div className="member-card__header">
          <div>
            {title ? <h2 className="member-card__title">{title}</h2> : null}
            {description ? <p className="member-card__desc">{description}</p> : null}
          </div>
          {action}
        </div>
      ) : null}
      {children}
    </section>
  )
}
