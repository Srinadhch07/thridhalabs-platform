/**
 * SectionHeader — eyebrow tag + display title for homepage sections,
 * with an optional action link on the right.
 */

import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'
import { Reveal } from './Reveal'

export interface SectionHeaderProps {
  tag: string
  title: ReactNode
  action?: { to: string; label: string }
  id?: string
}

export function SectionHeader({ tag, title, action, id }: SectionHeaderProps) {
  return (
    <Reveal className="section-head">
      <div>
        <p className="tag section-head__tag">
          <span className="hud-dot" aria-hidden="true" />
          {tag}
        </p>
        <h2 id={id} className="section-head__title">
          {title}
        </h2>
      </div>
      {action && (
        <Link className="section-head__action" to={action.to}>
          {action.label}
          <span className="arrow" aria-hidden="true">
            {' '}
            →
          </span>
        </Link>
      )}
    </Reveal>
  )
}