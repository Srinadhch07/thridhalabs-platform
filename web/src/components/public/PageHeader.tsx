/**
 * PageHeader — opening block for inner pages: HUD eyebrow, display title,
 * lede text and an optional meta row placed on the instrument grid.
 */

import type { ReactNode } from 'react'

export interface PageHeaderProps {
  eyebrow: string
  title: ReactNode
  lede?: ReactNode
  meta?: ReactNode
}

export function PageHeader({ eyebrow, title, lede, meta }: PageHeaderProps) {
  return (
    <section className="page-hero" aria-labelledby="page-title">
      <div className="shell page-hero__inner">
        <p className="eyebrow page-hero__eyebrow">
          <span className="hud-dot" aria-hidden="true" />
          {eyebrow}
        </p>
        <h1 id="page-title" className="page-hero__title">
          {title}
        </h1>
        {lede && <p className="page-hero__lede">{lede}</p>}
        {meta}
        <div className="page-hero__rule" aria-hidden="true" />
      </div>
    </section>
  )
}