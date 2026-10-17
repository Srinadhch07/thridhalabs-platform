/**
 * Inline SVG icons for the member portal navigation and accents.
 *
 * The project ships no icon dependency, so these are tiny hand-written SVGs
 * that inherit `currentColor` and scale with font-size context.
 */

import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement>

function base(props: IconProps) {
  return {
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.7,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    'aria-hidden': true,
    focusable: false,
    ...props,
  }
}

export function IconOverview(props: IconProps) {
  return (
    <svg className="member-nav__icon" {...base(props)}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  )
}

export function IconProfile(props: IconProps) {
  return (
    <svg className="member-nav__icon" {...base(props)}>
      <circle cx="12" cy="8" r="3.6" />
      <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
    </svg>
  )
}

export function IconAccount(props: IconProps) {
  return (
    <svg className="member-nav__icon" {...base(props)}>
      <path d="M12 3l7 3v5c0 4.4-3 8.3-7 10-4-1.7-7-5.6-7-10V6z" />
      <path d="M9.3 12l1.9 1.9 3.5-3.6" />
    </svg>
  )
}

export function IconWorks(props: IconProps) {
  return (
    <svg className="member-nav__icon" {...base(props)}>
      <rect x="3" y="4" width="18" height="14" rx="2" />
      <path d="M3 9h18" />
      <path d="M7 13h6" />
      <path d="M7 16h4" />
    </svg>
  )
}

export function IconCertification(props: IconProps) {
  return (
    <svg className="member-nav__icon" {...base(props)}>
      <circle cx="12" cy="9" r="5" />
      <path d="M8.5 13.5L7 21l5-2.5L17 21l-1.5-7.5" />
    </svg>
  )
}

export function IconActivities(props: IconProps) {
  return (
    <svg className="member-nav__icon" {...base(props)}>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M3 10h18M8 3v4M16 3v4" />
      <path d="M8 15h4" />
    </svg>
  )
}

export function IconProjects(props: IconProps) {
  return (
    <svg className="member-nav__icon" {...base(props)}>
      <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <path d="M3 11h18" />
    </svg>
  )
}

export function IconContributions(props: IconProps) {
  return (
    <svg className="member-nav__icon" {...base(props)}>
      <path d="M12 3l9 5-9 5-9-5z" />
      <path d="M3 12l9 5 9-5" />
      <path d="M3 16l9 5 9-5" />
    </svg>
  )
}

export function IconExternal(props: IconProps) {
  return (
    <svg className="member-nav__icon" {...base(props)}>
      <path d="M14 4h6v6" />
      <path d="M20 4l-8.5 8.5" />
      <path d="M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4" />
    </svg>
  )
}

export function IconCheck(props: IconProps) {
  return (
    <svg width="16" height="16" aria-hidden focusable="false" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M20 6L9 17l-5-5" />
    </svg>
  )
}
