/**
 * MemberLayout — authenticated member portal shell.
 *
 * Requires a valid member session (HttpOnly cookie backed); otherwise redirects
 * to /member/login preserving the intended destination. This is intentionally
 * separate from the admin layout: the member portal is not part of the Admin
 * Panel and exposes no admin navigation.
 *
 * The shell is responsive: a persistent sidebar on wide screens, and an
 * off-canvas drawer (Escape to close, focus managed, backdrop click) on
 * narrow ones.
 */

import { useEffect, useRef, useState } from 'react'
import { Navigate, Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { useMemberAuth } from '../../app/providers/MemberAuthProvider'
import { PageLoader } from '../ui/PageLoader'
import { SkipLink } from './SkipLink'
import { Main } from './Main'
import { MemberNav } from './MemberNav'
import { MemberAvatar } from '../member/MemberAvatar'

function RequireMember({ children }: { children: React.ReactNode }) {
  const { status } = useMemberAuth()
  const location = useLocation()

  if (status === 'loading') {
    return (
      <div className="site-shell">
        <Main>
          <PageLoader label="Checking session…" />
        </Main>
      </div>
    )
  }

  if (status === 'unauthenticated') {
    return <Navigate to="/member/login" replace state={{ from: location.pathname }} />
  }

  return <>{children}</>
}

export function MemberLayout() {
  const { member, signOut } = useMemberAuth()
  const navigate = useNavigate()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const toggleRef = useRef<HTMLButtonElement>(null)
  const drawerRef = useRef<HTMLDivElement>(null)
  const location = useLocation()

  useEffect(() => {
    setDrawerOpen(false)
  }, [location.pathname])

  useEffect(() => {
    if (!drawerOpen) return
    drawerRef.current?.focus()
    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === 'Escape') {
        setDrawerOpen(false)
        toggleRef.current?.focus()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [drawerOpen])

  async function handleSignOut(): Promise<void> {
    await signOut()
    navigate('/member/login', { replace: true })
  }

  const displayName = member?.full_name || 'Member'

  return (
    <RequireMember>
      <SkipLink />
      <div className="member-shell">
        <div
          ref={drawerRef}
          className={`member-sidebar${drawerOpen ? ' is-open' : ''}`}
          id="member-drawer"
          tabIndex={-1}
        >
          <Link to="/member" className="member-brand" onClick={() => setDrawerOpen(false)}>
            <span className="member-brand__mark" aria-hidden="true">
              TL
            </span>
            <span className="member-brand__text">
              <span className="member-brand__name">Thridha Labs</span>
              <span className="member-brand__area">Member area</span>
            </span>
          </Link>

          <div className="member-identity">
            <MemberAvatar name={displayName} size="sm" accent />
            <span className="member-identity__meta">
              <span className="member-identity__name">{displayName}</span>
              <span className="member-identity__id">{member?.member_id}</span>
            </span>
          </div>

          <MemberNav onNavigate={() => setDrawerOpen(false)} />
        </div>

        {drawerOpen ? (
          <div className="member-backdrop" onClick={() => setDrawerOpen(false)} aria-hidden="true" />
        ) : null}

        <div className="member-main-col">
          <header className="member-topbar">
            <button
              ref={toggleRef}
              type="button"
              className="btn btn--ghost btn--sm member-menu-toggle"
              aria-expanded={drawerOpen}
              aria-controls="member-drawer"
              onClick={() => setDrawerOpen((open) => !open)}
            >
              {drawerOpen ? 'Close' : 'Menu'}
            </button>
            <div className="member-topbar__spacer" />
            <div className="member-topbar__identity">
              <MemberAvatar name={displayName} size="sm" />
              <span className="member-topbar__name">{displayName}</span>
            </div>
            <button type="button" className="btn btn--ghost btn--sm" onClick={handleSignOut}>
              Sign out
            </button>
          </header>

          <main id="main-content" className="member-main" tabIndex={-1}>
            <Outlet />
          </main>
        </div>
      </div>
    </RequireMember>
  )
}
