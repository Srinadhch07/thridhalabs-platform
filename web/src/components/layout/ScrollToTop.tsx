/**
 * ScrollToTop — resets the window scroll position on route (pathname) changes.
 *
 * Without a data router (we use <BrowserRouter> + <Routes>), React Router does
 * not manage scroll, so the browser preserves the previous scroll position when
 * navigating between pages. This tiny component listens to the active location
 * and, whenever the PATHNAME changes, scrolls the window back to the top.
 *
 * Intentional hash navigation is preserved: when the URL carries a hash (e.g.
 * `/contact#reach`), we scroll to that element instead of the top. Re-renders
 * that do not change the pathname are ignored.
 */

import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

export function ScrollToTop() {
  const { pathname, hash } = useLocation()

  useEffect(() => {
    if (hash) {
      const target = document.getElementById(hash.slice(1))
      if (target) {
        target.scrollIntoView()
        return
      }
    }
    window.scrollTo(0, 0)
    // Only re-run on an actual pathname change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname])

  return null
}
