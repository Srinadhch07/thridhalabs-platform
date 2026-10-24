/**
 * Cookie consent banner and preferences
 */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getCookieConsent, setCookieConsent } from '../../lib/utils/cookieConsent'

export function CookieConsentBanner() {
  const [showBanner, setShowBanner] = useState(false)
  const [showCustomize, setShowCustomize] = useState(false)
  const [analytics, setAnalytics] = useState(false)
  const [marketing, setMarketing] = useState(false)

  useEffect(() => {
    const existing = getCookieConsent()
    if (!existing) {
      setShowBanner(true)
    }

    const handler = (e: Event) => {
      const custom = e as CustomEvent
      if (custom.detail === 'open') {
        setShowCustomize(true)
        setShowBanner(true)
        const existing2 = getCookieConsent()
        setAnalytics(!!existing2?.analytics)
        setMarketing(!!existing2?.marketing)
      }
    }
    window.addEventListener('thridha:cookie-preferences' as any, handler)
    return () => window.removeEventListener('thridha:cookie-preferences' as any, handler)
  }, [])

  useEffect(() => {
    const openers = document.querySelectorAll('[data-cookie-preferences]')
    const onClick = () => {
      window.dispatchEvent(new CustomEvent('thridha:cookie-preferences', { detail: 'open' }))
    }
    openers.forEach((el) => el.addEventListener('click', onClick))
    return () => openers.forEach((el) => el.removeEventListener('click', onClick))
  }, [])

  const acceptAll = () => {
    setCookieConsent({ analytics: true, marketing: true })
    setShowBanner(false)
    setShowCustomize(false)
  }

  const rejectNonEssential = () => {
    setCookieConsent({ analytics: false, marketing: false })
    setShowBanner(false)
    setShowCustomize(false)
  }

  const saveCustom = () => {
    setCookieConsent({ analytics, marketing })
    setShowBanner(false)
    setShowCustomize(false)
  }

  if (!showBanner) return null

  return (
    <div className="cookie-consent" role="dialog" aria-modal="true" aria-labelledby="cookie-consent-title">
      <div className="cookie-consent__backdrop" aria-hidden="true" />
      <div className="cookie-consent__panel" role="document">
        {!showCustomize ? (
          <div className="cookie-consent__content">
            <div className="cookie-consent__header">
              <h2 id="cookie-consent-title" className="cookie-consent__title">
                Cookie preferences
              </h2>
              <p className="cookie-consent__text">
                We use strictly necessary storage to keep the site working. Optional categories are only used with your consent.
                See our <Link to="/privacy-policy">Privacy Policy</Link>.
              </p>
            </div>
            <div className="cookie-consent__actions">
              <button type="button" className="cookie-consent__btn cookie-consent__btn--ghost" onClick={rejectNonEssential}>
                Reject Non-Essential
              </button>
              <button type="button" className="cookie-consent__btn cookie-consent__btn--ghost" onClick={() => setShowCustomize(true)}>
                Customize
              </button>
              <button type="button" className="cookie-consent__btn cookie-consent__btn--primary" onClick={acceptAll}>
                Accept All
              </button>
            </div>
          </div>
        ) : (
          <div className="cookie-consent__content">
            <div className="cookie-consent__header">
              <h2 className="cookie-consent__title">Customize preferences</h2>
              <p className="cookie-consent__text">
                Choose which categories to allow. Strictly necessary storage cannot be disabled when required for core functionality.
              </p>
            </div>
            <div className="cookie-consent__categories">
              <div className="cookie-consent__category">
                <div className="cookie-consent__category-head">
                  <span className="cookie-consent__category-title">Strictly Necessary</span>
                  <span className="cookie-consent__category-state">Always enabled</span>
                </div>
                <p className="cookie-consent__category-desc">Required for core website functionality (e.g., sessions/authentication).</p>
              </div>
              <label className="cookie-consent__category cookie-consent__category--toggle">
                <div className="cookie-consent__category-head">
                  <span className="cookie-consent__category-title">Analytics</span>
                  <input type="checkbox" checked={analytics} onChange={(e) => setAnalytics(e.target.checked)} />
                </div>
                <p className="cookie-consent__category-desc">Helps understand usage. Only enabled with consent if present.</p>
              </label>
              <label className="cookie-consent__category cookie-consent__category--toggle">
                <div className="cookie-consent__category-head">
                  <span className="cookie-consent__category-title">Marketing</span>
                  <input type="checkbox" checked={marketing} onChange={(e) => setMarketing(e.target.checked)} />
                </div>
                <p className="cookie-consent__category-desc">Marketing trackers. Only enabled with consent if present.</p>
              </label>
            </div>
            <div className="cookie-consent__actions">
              <button type="button" className="cookie-consent__btn cookie-consent__btn--ghost" onClick={rejectNonEssential}>
                Reject Non-Essential
              </button>
              <button type="button" className="cookie-consent__btn cookie-consent__btn--ghost" onClick={() => setShowCustomize(false)}>
                Back
              </button>
              <button type="button" className="cookie-consent__btn cookie-consent__btn--primary" onClick={saveCustom}>
                Save Preferences
              </button>
            </div>
            <p className="cookie-consent__footnote">
              <Link to="/privacy-policy">Privacy Policy</Link> · <Link to="/terms-and-conditions">Terms &amp; Conditions</Link>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
