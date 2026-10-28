/**
 * Member portal navigation.
 *
 * Icons are decorative (`aria-hidden`); each link keeps its visible label and
 * `NavLink`'s automatic `aria-current="page"` marks the active destination.
 */

import type { ComponentType, SVGProps } from 'react'
import { NavLink } from 'react-router-dom'
import {
  IconActivities,
  IconAccount,
  IconCertification,
  IconContributions,
  IconExternal,
  IconOverview,
  IconProfile,
  IconProjects,
  IconWorks,
} from '../member/icons'

interface NavItem {
  to: string
  label: string
  end?: boolean
  Icon: ComponentType<SVGProps<SVGSVGElement>>
}

const NAV_ITEMS: NavItem[] = [
  { to: '/member', label: 'Overview', end: true, Icon: IconOverview },
  { to: '/member/works', label: 'Work Showcase', Icon: IconWorks },
  { to: '/member/activities', label: 'My Activities', Icon: IconActivities },
  { to: '/member/projects', label: 'My Projects', Icon: IconProjects },
  { to: '/member/contributions', label: 'Contributions', Icon: IconContributions },
  { to: '/member/certifications', label: 'Certifications', Icon: IconCertification },
  { to: '/member/profile', label: 'My Profile', Icon: IconProfile },
  { to: '/member/account', label: 'Account Settings', Icon: IconAccount },
]

export function MemberNav({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="member-nav" aria-label="Member portal">
      <ul className="member-nav__list">
        {NAV_ITEMS.map(({ to, label, end, Icon }) => (
          <li key={to}>
            <NavLink
              to={to}
              end={end}
              onClick={onNavigate}
              className={({ isActive }) => `member-nav__link${isActive ? ' is-active' : ''}`}
            >
              <Icon />
              <span>{label}</span>
            </NavLink>
          </li>
        ))}
        <li className="member-nav__sep" role="separator" />
        <li>
          <NavLink to="/" className="member-nav__link member-nav__link--muted">
            <IconExternal />
            <span>View public site</span>
          </NavLink>
        </li>
      </ul>
    </nav>
  )
}
