/** Provider tests — settings availability, maintenance flag, branding CSS vars. */

import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SiteSettingsProvider, useSiteSettings } from '../app/providers/SiteSettingsProvider'
import { BrandingProvider, useBranding } from '../app/providers/BrandingProvider'
import { BRANDING_CSS_VARS } from '../lib/utils/brandingTheme'
import { installFetchMock } from './helpers'
import { brandingFixture, settingsFixture } from './fixtures'
import type { PublicSiteSettings } from '../types/settings'

function SettingsProbe() {
  const { status, data, maintenanceEnabled } = useSiteSettings()
  return (
    <div>
      <span data-testid="settings-status">{status}</span>
      <span data-testid="settings-name">{data?.general.site_name ?? 'none'}</span>
      <span data-testid="settings-maintenance">{String(maintenanceEnabled)}</span>
    </div>
  )
}

function renderSettings(handlers: Parameters<typeof installFetchMock>[0]) {
  installFetchMock(handlers)
  return render(
    <SiteSettingsProvider>
      <SettingsProbe />
    </SiteSettingsProvider>,
  )
}

describe('SiteSettingsProvider', () => {
  it('exposes loaded settings and maintenance disabled by default', async () => {
    renderSettings({ '/api/public/settings': { body: settingsFixture } })
    expect(screen.getByTestId('settings-status').textContent).toBe('loading')
    await waitFor(() => expect(screen.getByTestId('settings-name').textContent).toBe('Thridha Labs'))
    expect(screen.getByTestId('settings-status').textContent).toBe('success')
    expect(screen.getByTestId('settings-maintenance').textContent).toBe('false')
  })

  it('honours maintenance_mode when present in the payload', async () => {
    renderSettings({
      '/api/public/settings': { body: { ...settingsFixture, maintenance_mode: true } as PublicSiteSettings },
    })
    await waitFor(() => expect(screen.getByTestId('settings-status').textContent).toBe('success'))
    expect(screen.getByTestId('settings-maintenance').textContent).toBe('true')
  })

  it('ends in the error state without crashing when settings are unavailable', async () => {
    renderSettings({ '/api/public/settings': { status: 503, body: { error: { code: 'DOWN' } } } })
    await waitFor(() => expect(screen.getByTestId('settings-status').textContent).toBe('error'))
    expect(screen.getByTestId('settings-name').textContent).toBe('none')
    expect(screen.getByTestId('settings-maintenance').textContent).toBe('false')
  })
})

function BrandingProbe() {
  const { status, data } = useBranding()
  return (
    <div>
      <span data-testid="branding-status">{status}</span>
      <span data-testid="branding-primary">{data?.colors.primary ?? 'none'}</span>
    </div>
  )
}

function renderBranding(handlers: Parameters<typeof installFetchMock>[0]) {
  installFetchMock(handlers)
  return render(
    <BrandingProvider>
      <BrandingProbe />
    </BrandingProvider>,
  )
}

describe('BrandingProvider', () => {
  it('applies branding colors as CSS variables on <html>', async () => {
    const fixture = { ...brandingFixture, colors: { ...brandingFixture.colors, primary: '#ff00aa' } }
    renderBranding({ '/api/public/branding': { body: fixture } })
    await waitFor(() => expect(screen.getByTestId('branding-status').textContent).toBe('success'))
    expect(document.documentElement.style.getPropertyValue(BRANDING_CSS_VARS.primary)).toBe('#ff00aa')
    expect(document.documentElement.style.colorScheme).toBe('light')
  })

  it('applies a dark-mode branding across all five variables', async () => {
    const fixture = {
      ...brandingFixture,
      mode: 'dark',
      colors: { primary: '#a78bfa', secondary: '#e879f9', accent: '#c4b5fd', background: '#111014', text: '#faf7ff' },
    }
    renderBranding({ '/api/public/branding': { body: fixture } })
    await waitFor(() => expect(screen.getByTestId('branding-status').textContent).toBe('success'))
    const root = document.documentElement
    expect(root.style.colorScheme).toBe('dark')
    expect(root.style.getPropertyValue(BRANDING_CSS_VARS.primary)).toBe('#a78bfa')
    expect(root.style.getPropertyValue(BRANDING_CSS_VARS.secondary)).toBe('#e879f9')
    expect(root.style.getPropertyValue(BRANDING_CSS_VARS.accent)).toBe('#c4b5fd')
    expect(root.style.getPropertyValue(BRANDING_CSS_VARS.background)).toBe('#111014')
    expect(root.style.getPropertyValue(BRANDING_CSS_VARS.text)).toBe('#faf7ff')
  })

  it('keeps the fallback palette when branding is unavailable', async () => {
    renderBranding({ '/api/public/branding': { status: 503, body: { error: { code: 'DOWN' } } } })
    await waitFor(() => expect(screen.getByTestId('branding-status').textContent).toBe('error'))
    expect(screen.getByTestId('branding-primary').textContent).toBe('none')
    expect(document.documentElement.hasAttribute('style')).toBe(false)
  })
})