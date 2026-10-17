/** Branding designer tests — theme presets, live preview, custom palette
 * detection, hex validation, persistence via PUT and reload restoration. */

import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { adminBrandingFixture, adminDataHandlers } from './fixtures'
import { renderApp, type FetchCall } from './helpers'
import type { AdminBranding } from '../types/branding'

function getHexInput(label: string): HTMLInputElement {
  return screen.getByLabelText(`${label} \u2014 hex value`) as HTMLInputElement
}

function brandingCalls(calls: FetchCall[]): FetchCall[] {
  return calls.filter((c) => c.url.includes('/api/branding'))
}

function putBody(call: FetchCall | undefined): Record<string, unknown> {
  expect(call).toBeTruthy()
  return JSON.parse(String(call!.init?.body)) as Record<string, unknown>
}

describe('admin branding themes', () => {
  it('renders all six theme presets across light and dark', async () => {
    renderApp({ entry: '/admin/branding', handlers: adminDataHandlers() })
    await screen.findByRole('radio', { name: /arctic white theme/i })

    expect(screen.getByRole('radio', { name: /arctic white theme/i })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /ivory & indigo theme/i })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /pearl & emerald theme/i })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /midnight slate theme/i })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /obsidian & violet theme/i })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /graphite & amber theme/i })).toBeInTheDocument()

    expect(screen.getByText(/choose a theme as your starting point/i)).toBeInTheDocument()
  })

  it('selecting a preset paints the color inputs, mode, preview and selection state', async () => {
    const { calls } = renderApp({ entry: '/admin/branding', handlers: adminDataHandlers() })
    const radio = await screen.findByRole('radio', { name: /obsidian & violet theme/i })
    fireEvent.click(radio)

    expect(screen.getByRole('radio', { name: /obsidian & violet theme/i })).toBeChecked()
    expect(getHexInput('Primary').value).toBe('#a78bfa')
    expect(getHexInput('Secondary').value).toBe('#e879f9')
    expect(getHexInput('Accent').value).toBe('#c4b5fd')
    expect(getHexInput('Background').value).toBe('#111014')
    expect(getHexInput('Text').value).toBe('#faf7ff')
    expect(screen.getByLabelText('Default theme')).toHaveValue('dark')

    const preview = document.querySelector('.branding-preview')
    expect(preview).toBeTruthy()
    expect(preview!.getAttribute('data-mode')).toBe('dark')
    const panel = document.querySelector('.branding-preview__panel') as HTMLElement
    expect(panel.style.getPropertyValue('--sw-primary')).toBe('#a78bfa')
    expect(panel.style.getPropertyValue('--sw-bg')).toBe('#111014')

    const check = document.querySelector('.theme-card--selected .theme-card__check')
    expect(check).toBeTruthy()
    expect(brandingCalls(calls).length).toBe(1) // initial GET only — no save yet
  })

  it('customizing a color deselects the preset and flags the palette as custom', async () => {
    renderApp({ entry: '/admin/branding', handlers: adminDataHandlers() })
    const radio = await screen.findByRole('radio', { name: /pearl & emerald theme/i })
    fireEvent.click(radio)
    expect(screen.getByRole('radio', { name: /pearl & emerald theme/i })).toBeChecked()

    fireEvent.change(getHexInput('Primary'), { target: { value: '#123456' } })

    expect(getHexInput('Primary').value).toBe('#123456')
    expect(screen.getByRole('radio', { name: /pearl & emerald theme/i })).not.toBeChecked()
    expect(document.querySelector('.theme-status--custom')).toHaveTextContent('Custom')
    expect(document.querySelector('.theme-card--selected')).toBeNull()

    const preview = document.querySelector('.branding-preview__panel') as HTMLElement
    expect(preview.style.getPropertyValue('--sw-primary')).toBe('#123456')
  })

  it('shows an inline error for an invalid hex without breaking the preview', async () => {
    renderApp({ entry: '/admin/branding', handlers: adminDataHandlers() })
    await screen.findByRole('radio', { name: /arctic white theme/i })

    fireEvent.change(getHexInput('Primary'), { target: { value: '#12gf45' } })

    expect(screen.getByText(/enter a #rrggbb hex value/i)).toBeInTheDocument()
    const preview = document.querySelector('.branding-preview__panel') as HTMLElement
    expect(preview.style.getPropertyValue('--sw-primary')).toBe('#4f46e5') // last valid kept

    fireEvent.change(getHexInput('Primary'), { target: { value: '#123456' } })
    expect(screen.queryByText(/enter a #rrggbb hex value/i)).not.toBeInTheDocument()
    expect(preview.style.getPropertyValue('--sw-primary')).toBe('#123456')
  })

  it('keeps the picker in sync with the validated hex text', async () => {
    renderApp({ entry: '/admin/branding', handlers: adminDataHandlers() })
    await screen.findByRole('radio', { name: /arctic white theme/i })

    fireEvent.change(getHexInput('Accent'), { target: { value: '#FF0000' } })
    expect(getHexInput('Accent').value).toBe('#ff0000') // normalized lowercase

    const swatch = screen.getByLabelText('Accent') as HTMLInputElement
    expect(swatch.type).toBe('color')
    expect(swatch.value).toBe('#ff0000')
  })
})

describe('admin branding persistence', () => {
  it('saves the chosen preset through the API and restores it on reload', async () => {
    let stored: AdminBranding = adminBrandingFixture
    const handlers = {
      ...adminDataHandlers(),
      '/api/branding': (_url: string, init?: RequestInit) => {
        if (init?.method === 'PUT') {
          stored = {
            ...adminBrandingFixture,
            ...(JSON.parse(String(init.body)) as Partial<AdminBranding>),
          }
        }
        return { body: stored }
      },
    }

    const { calls } = renderApp({ entry: '/admin/branding', handlers })
    const radio = await screen.findByRole('radio', { name: /obsidian & violet theme/i })
    fireEvent.click(radio)

    fireEvent.click(screen.getByRole('button', { name: /save branding/i }))
    await waitFor(() => {
      const puts = brandingCalls(calls).filter((c) => c.init?.method === 'PUT')
      expect(puts).toHaveLength(1)
    })

    const body = putBody(brandingCalls(calls).find((c) => c.init?.method === 'PUT'))
    expect(body.theme_preset).toBe('obsidian_violet')
    expect(body.mode).toBe('dark')
    const colors = body.colors as Record<string, string>
    expect(colors.primary).toBe('#a78bfa')
    expect(colors.text).toBe('#faf7ff')
    expect(body.media).toEqual({
      logo: null,
      logo_dark: null,
      logo_light: null,
      favicon: null,
      og_image: null,
    })

    // reloads re-hydrate from the saved value
    await waitFor(() => {
      expect(screen.getByRole('radio', { name: /obsidian & violet theme/i })).toBeChecked()
    })
    expect(document.querySelector('.theme-status--custom')).toBeNull()
    expect(screen.queryByText(/unsaved changes/i)).not.toBeInTheDocument()
  })

  it('persists custom palettes and keeps them distinct from presets', async () => {
    let stored: AdminBranding = adminBrandingFixture
    const handlers = {
      ...adminDataHandlers(),
      '/api/branding': (_url: string, init?: RequestInit) => {
        if (init?.method === 'PUT') {
          stored = {
            ...adminBrandingFixture,
            ...(JSON.parse(String(init.body)) as Partial<AdminBranding>),
          }
        }
        return { body: stored }
      },
    }

    const { calls } = renderApp({ entry: '/admin/branding', handlers })
    await screen.findByRole('radio', { name: /graphite & amber theme/i })
    fireEvent.change(getHexInput('Primary'), { target: { value: '#123456' } })

    fireEvent.click(screen.getByRole('button', { name: /save branding/i }))
    await waitFor(() => {
      expect(brandingCalls(calls).filter((c) => c.init?.method === 'PUT')).toHaveLength(1)
    })

    const body = putBody(brandingCalls(calls).find((c) => c.init?.method === 'PUT'))
    expect(body.theme_preset).toBeNull()

    // after reload the customized palette is still shown as custom
    await waitFor(() => {
      expect(document.querySelector('.theme-status--custom')).toHaveTextContent('Custom')
    })
    expect(getHexInput('Primary').value).toBe('#123456')
  })
})