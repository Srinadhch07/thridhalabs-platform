/**
 * Public site header — brand wordmark, primary navigation and a thin
 * scroll-progress readout beneath the bar. Settings-driven brand name with a
 * ghost-stroked "Labs" when the site is still branded Thridha Labs.
 */

import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useSiteSettings } from '../../app/providers/SiteSettingsProvider'
import { useBranding } from '../../app/providers/BrandingProvider'
import { getDefaultLogoUrl, resolveMediaUrl } from '../../lib/utils/mediaUrl'
import { Navigation } from './Navigation'

function brandMark(siteName: string) {
  const match = /^thridha labs$/i.test(siteName)
  if (match) {
    return <>Thridha Labs</>
  }
  return siteName
}

export function Header() {
  const { data: settings } = useSiteSettings()
  const { data: branding } = useBranding()
  const siteName = settings?.general.site_name || 'Thridha Labs'
  const headerRef = useRef<HTMLElement | null>(null)
  const logo =
    resolveMediaUrl(branding?.media.logo, 'thumb') ||
    resolveMediaUrl(branding?.media.logo_light ?? branding?.media.logo_dark, 'thumb') ||
    getDefaultLogoUrl()

  useEffect(() => {
    const headerElement = headerRef.current
    if (!headerElement) return
    const host: HTMLElement = headerElement

    function updateProgress(): void {
      const scrollable = document.documentElement.scrollHeight - window.innerHeight
      const progress = scrollable > 0 ? Math.min(100, (window.scrollY / scrollable) * 100) : 0
      host.style.setProperty('--scroll-progress', `${progress}%`)
    }

    updateProgress()
    window.addEventListener('scroll', updateProgress, { passive: true })
    window.addEventListener('resize', updateProgress)
    return () => {
      window.removeEventListener('scroll', updateProgress)
      window.removeEventListener('resize', updateProgress)
    }
  }, [])

  return (
    <header className="site-header public-header" ref={headerRef}>
      <div className="public-header__inner">
        <Link to="/" className="public-brand" aria-label={siteName}>
          {logo ? (
            <img className="public-brand__logo" src={logo} alt={`${siteName} logo`} decoding="async" />
          ) : null}
          {brandMark(siteName)}
        </Link>
        <Navigation />
        <div className="header-actions">
          <Link to="/contact" className="header-cta">
            Start a project
          </Link>
          <Link to="/member/login" className="header-login">
            Member Login
          </Link>
        </div>
      </div>
      <div className="public-header__progress" aria-hidden="true" />
    </header>
  )
}