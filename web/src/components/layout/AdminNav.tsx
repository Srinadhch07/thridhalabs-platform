/** Admin sidebar navigation. */

import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/admin', label: 'Dashboard', end: true },
  { to: '/admin/clients', label: 'Clients', end: false },
  { to: '/admin/projects', label: 'Projects', end: false },
  { to: '/admin/activities', label: 'Activities', end: false },
  { to: '/admin/testimonials', label: 'Testimonials', end: false },
  { to: '/admin/careers', label: 'Careers', end: false },
  { to: '/admin/members', label: 'Members', end: false },
  { to: '/admin/works', label: 'Publication review', end: false },
  { to: '/admin/reports', label: 'Progress reports', end: false },
  { to: '/admin/certifications', label: 'Certifications', end: false },
  { to: '/admin/certificates', label: 'Certificates', end: false },
  { to: '/admin/activity-certificates', label: 'Activity certificates', end: false },
  { to: '/admin/media', label: 'Media', end: false },
  { to: '/admin/settings', label: 'Settings', end: false },
  { to: '/admin/branding', label: 'Branding', end: false },
  { to: '/admin/legal', label: 'Legal Pages', end: false },
  { to: '/admin/ai/settings', label: 'AI Settings', end: false },
  { to: '/admin/ai/summaries', label: 'AI Summaries', end: false },
  { to: '/admin/account', label: 'Account', end: false },
] as const

export function AdminNav({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="admin-nav" aria-label="Admin">
      <ul className="admin-nav__list">
        {NAV_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.end}
              onClick={onNavigate}
              className={({ isActive }) => `admin-nav__link${isActive ? ' is-active' : ''}`}
            >
              {item.label}
            </NavLink>
          </li>
        ))}
        <li className="admin-nav__sep" role="separator" />
        <li>
          <NavLink
            to="/"
            className="admin-nav__link"
          >
            View public site
          </NavLink>
        </li>
      </ul>
    </nav>
  )
}
