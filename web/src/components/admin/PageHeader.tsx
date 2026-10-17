/** Admin page header — eyebrow, title, optional description and action. */

import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

export interface PageHeaderProps {
  eyebrow: string
  title: string
  description?: string
  actionLabel?: string
  actionTo?: string
  children?: ReactNode
}

export function PageHeader({ eyebrow, title, description, actionLabel, actionTo, children }: PageHeaderProps) {
  return (
    <div className="admin-page-header">
      <div className="admin-page-header__text">
        <p className="eyebrow">{eyebrow}</p>
        <h1 style={{ fontSize: 'var(--fs-lg)' }}>{title}</h1>
        {description ? <p className="admin-page-header__description">{description}</p> : null}
        {children}
      </div>
      {actionLabel && actionTo ? (
        <Link className="btn btn--primary" to={actionTo}>
          {actionLabel}
        </Link>
      ) : null}
    </div>
  )
}