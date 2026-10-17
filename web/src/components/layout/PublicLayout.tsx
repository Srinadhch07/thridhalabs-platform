/**
 * Public layout — structural shell for the public website.
 *
 * Renders the shared Header/Main/Footer plus the maintenance gate. While site
 * settings load, content shows a loading state; the header/footer still render
 * so navigation is never blank. `.site-main--public` makes the content area
 * full-bleed (pages manage their own `.shell` containers).
 */

import { Outlet } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useSiteSettings } from '../../app/providers/SiteSettingsProvider'
import { PageLoader } from '../ui/PageLoader'
import { SkipLink } from './SkipLink'
import { Header } from './Header'
import { Main } from './Main'
import { Footer } from './Footer'
import MaintenancePage from '../../pages/public/MaintenancePage'

/** Renders the maintenance page instead of children when enabled. */
export function MaintenanceGuard({ enabled, children }: { enabled: boolean; children: ReactNode }) {
  if (enabled) {
    return <MaintenancePage />
  }
  return <>{children}</>
}

export function PublicLayout() {
  const { status, maintenanceEnabled } = useSiteSettings()

  const content: ReactNode =
    status === 'loading' ? (
      <PageLoader label="Booting the lab" />
    ) : (
      <MaintenanceGuard enabled={maintenanceEnabled}>
        <Outlet />
      </MaintenanceGuard>
    )

  return (
    <div className="site-shell public-shell">
      <SkipLink />
      <Header />
      <Main className="site-main--public">{content}</Main>
      <Footer />
    </div>
  )
}