/** Application main content region. */

import type { ReactNode } from 'react'

export function Main({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <main id="main-content" className={`site-main${className ? ` ${className}` : ''}`} tabIndex={-1}>
      {children}
    </main>
  )
}