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
  /** Heading level for the title. Defaults to 2; pass 1 for a page's only h1. */
  level?: 1 | 2
}

export function SectionHeader({ tag, title, action, id, level = 2 }: SectionHeaderProps) {
  const Heading = level === 1 ? 'h1' : 'h2'
  return (
    <Reveal className="section-head">
      <div>
        <p className="tag section-head__tag">
          <span className="hud-dot" aria-hidden="true" />
          {tag}
        </p>
        <Heading id={id} className="section-head__title">
          {title}
        </Heading>
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