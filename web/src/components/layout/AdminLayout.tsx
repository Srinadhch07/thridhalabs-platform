/**
 * AdminLayout — authenticated admin shell.
 *
 * - Requires a valid session (HttpOnly cookie backed); otherwise redirects to
 *   /admin/login preserving the intended destination.
 * - Sidebar navigation (responsive drawer on small screens: Escape closes,
 *   focus is managed, backdrop click closes).
 * - Header shows the signed-in account; account/sign-out live in the header.
 */

import { useEffect, useRef, useState } from 'react'
import { Navigate, Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../app/providers/AuthProvider'
import { ROLE_LABELS } from '../../features/auth/rbac'
import { PageLoader } from '../ui/PageLoader'
import { Main } from './Main'
import { AdminNav } from './AdminNav'
import { AdminRouteBoundary } from './AdminRouteBoundary'

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { status } = useAuth()
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
    return <Navigate to="/admin/login" replace state={{ from: location.pathname }} />
  }

  return <>{children}</>
}

export function AdminLayout() {
  const { user, signOut } = useAuth()
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
    navigate('/admin/login', { replace: true })
  }

  return (
    <AdminRouteBoundary>
      <RequireAdmin>
        <div className="admin-shell">
          <div
            ref={drawerRef}
            className={`admin-drawer${drawerOpen ? ' is-open' : ''}`}
            id="admin-drawer"
            tabIndex={-1}
          >
            <div className="admin-drawer__brand">
              <p className="eyebrow">Control center</p>
              <Link to="/admin" className="site-brand" onClick={() => setDrawerOpen(false)}>
                {user?.email ? user.email.split('@')[0] : 'Admin'}
              </Link>
            </div>
            <AdminNav onNavigate={() => setDrawerOpen(false)} />
          </div>

          {drawerOpen ? (
            <div
              className="admin-backdrop"
              onClick={() => setDrawerOpen(false)}
              aria-hidden="true"
            />
          ) : null}

          <div className="admin-main-col">
            <header className="admin-topbar">
              <button
                ref={toggleRef}
                type="button"
                className="btn btn--ghost btn--sm admin-menu-toggle"
                aria-expanded={drawerOpen}
                aria-controls="admin-drawer"
                onClick={() => setDrawerOpen((open) => !open)}
              >
                {drawerOpen ? 'Close' : 'Menu'}
              </button>
              <div className="admin-topbar__spacer" />
              <div className="admin-account">
                <span className="admin-account__email">{user?.email}</span>
                <span className="admin-account__role">{user ? ROLE_LABELS[user.role] : ''}</span>
                <button type="button" className="btn btn--ghost btn--sm" onClick={handleSignOut}>
                  Sign out
                </button>
              </div>
            </header>

            <Main className="admin-main">
              <Outlet />
            </Main>
          </div>
        </div>
      </RequireAdmin>
    </AdminRouteBoundary>
  )
}