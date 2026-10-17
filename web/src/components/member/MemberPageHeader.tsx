/**
 * MemberPageHeader — consistent title block for every member portal page.
 */

import type { ReactNode } from 'react'

interface MemberPageHeaderProps {
  eyebrow?: string
  title: string
  description?: string
  actions?: ReactNode
}

export function MemberPageHeader({
  eyebrow = 'Member portal',
  title,
  description,
  actions,
}: MemberPageHeaderProps) {
  return (
    <div className="member-page-header">
      <div className="member-page-header__main">
        <p className="eyebrow">{eyebrow}</p>
        <h1 className="member-page-header__title">{title}</h1>
        {description ? <p className="member-page-header__desc">{description}</p> : null}
      </div>
      {actions ? <div className="member-page-header__actions">{actions}</div> : null}
    </div>
  )
}
