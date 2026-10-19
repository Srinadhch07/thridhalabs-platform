/**
 * Navigation — single "Primary" landmark used for both desktop and mobile.
 *
 * On desktop the wrapper is inline; from 900px down it becomes a fixed overlay
 * panel toggled by the menu button. Keyboard behaviour: Escape closes, focus is
 * trapped inside the open menu, body scroll is locked, and focus is returned
 * to the trigger on close. The mobile panel is fully opaque and layered above
 * page content so the labels always keep strong contrast.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { useCareers } from '../../app/providers/CareersProvider'

const BASE_NAV_ITEMS = [
  { to: '/projects', label: 'Projects' },
  { to: '/activities', label: 'Activities' },
  { to: '/clients', label: 'Clients' },
  { to: '/testimonials', label: 'Testimonials' },
  { to: '/about', label: 'About' },
  { to: '/contact', label: 'Contact' },
] as const

function HomeIcon() {
  return (
    <svg
      className="public-nav__icon"
      viewBox="0 0 24 24"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M3.5 10.5 12 4l8.5 6.5" />
      <path d="M5.5 9.5V19h13V9.5" />
      <path d="M10 19v-5h4v5" />
    </svg>
  )
}

export function Navigation() {
  const [open, setOpen] = useState(false)
  const buttonRef = useRef<HTMLButtonElement | null>(null)
  const panelRef = useRef<HTMLDivElement | null>(null)
  const location = useLocation()
  const { enabled: careersEnabled } = useCareers()

  const close = useCallback(() => setOpen(false), [])

  const navItems = careersEnabled
    ? [...BASE_NAV_ITEMS, { to: '/careers', label: 'Careers' }]
    : BASE_NAV_ITEMS

  useEffect(() => {
    close()
  }, [location, close])

  useEffect(() => {
    if (!open) return
    const previouslyFocused = document.activeElement as HTMLElement | null

    document.body.style.overflow = 'hidden'

    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === 'Escape') {
        setOpen(false)
      }
    }

    function onFocusIn(event: FocusEvent): void {
      const target = event.target as Node | null
      if (!panelRef.current?.contains(target) && target !== buttonRef.current) {
        buttonRef.current?.focus()
      }
    }

    window.addEventListener('keydown', onKeyDown)
    document.addEventListener('focusin', onFocusIn)

    return () => {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', onKeyDown)
      document.removeEventListener('focusin', onFocusIn)
      previouslyFocused?.focus()
    }
  }, [open])

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        className="menu-toggle"
        aria-expanded={open}
        aria-controls="public-site-menu"
        onClick={() => setOpen((value) => !value)}
      >
        <span className="menu-toggle__bars" aria-hidden="true">
          <span />
          <span />
          <span />
        </span>
        <span className="visually-hidden">{open ? 'Close menu' : 'Open menu'}</span>
      </button>

      <div
        ref={panelRef}
        id="public-site-menu"
        className={`mobile-menu${open ? ' is-open' : ''}`}
      >
        <nav className="public-nav" aria-label="Primary">
          <ul className="public-nav__list">
            <li>
              <NavLink to="/" end onClick={close} className="public-nav__home">
                <HomeIcon />
                Home
              </NavLink>
            </li>
            {navItems.map((item) => (
              <li key={item.to}>
                <NavLink to={item.to} onClick={close}>
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className="public-nav__actions">
          <Link to="/member/login" className="public-nav__login" onClick={close}>
            Member Login
          </Link>
          <Link to="/contact" className="public-nav__cta" onClick={close}>
            Start a project
          </Link>
        </div>
      </div>
    </>
  )
}
