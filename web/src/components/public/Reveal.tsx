/**
 * Reveal — scroll-in wrapper driven by IntersectionObserver.
 *
 * Pure CSS transition (opacity/translate); fully disabled under
 * prefers-reduced-motion via a media query. Defaults to visible
 * whenever the observer API is unavailable (older engines, jsdom).
 */

import { useEffect, useRef, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'

export interface RevealProps {
  children: ReactNode
  className?: string
  /** Stagger delay in milliseconds (applied as a CSS transition delay). */
  delay?: number
  id?: string
  style?: CSSProperties
}

export function Reveal({ children, className = '', delay = 0, id, style }: RevealProps) {
  const ref = useRef<HTMLDivElement | null>(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const node = ref.current
    if (!node) return

    const reducedMotion =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (reducedMotion || typeof IntersectionObserver === 'undefined') {
      setInView(true)
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setInView(true)
            observer.disconnect()
            break
          }
        }
      },
      { threshold: 0.12, rootMargin: '0px 0px -8% 0px' },
    )

    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  return (
    <div
      ref={ref}
      id={id}
      className={`reveal${inView ? ' is-in' : ''}${className ? ` ${className}` : ''}`}
      style={{ ...style, ['--rd' as string]: `${delay}ms` }}
    >
      {children}
    </div>
  )
}