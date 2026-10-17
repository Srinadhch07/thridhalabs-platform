/**
 * BrandingPreview — a scoped live preview of the current branding values.
 *
 * The preview maps the five stored colors onto the exact surface derivation
 * ratios the real site uses (see tokens.css: --panel/--panel-2/--frame/
 * --frame-soft/--text-dim/--on-accent), so the preview and the live site
 * render from the same single color system. Everything is scoped to this
 * container via --sw-* custom properties — nothing leaks onto :root.
 */

import type { BrandingColors, BrandingMode } from '../../types/branding'
import { inkOn } from '../../lib/utils/brandingPresets'

export interface BrandingPreviewProps {
  colors: BrandingColors
  mode: BrandingMode
}

export function BrandingPreview({ colors, mode }: BrandingPreviewProps) {
  return (
    <div className="branding-preview" data-mode={mode}>
      <div
        className="branding-preview__panel"
        style={{
          '--sw-bg': colors.background,
          '--sw-primary': colors.primary,
          '--sw-secondary': colors.secondary,
          '--sw-accent': colors.accent,
          '--sw-text': colors.text,
          background: 'var(--sw-bg)',
          color: 'var(--sw-text)',
        } as React.CSSProperties}
      >
        <div
          className="branding-preview__surface"
          style={{ '--sw-surface': 'color-mix(in srgb, var(--sw-text) 5%, transparent)' } as React.CSSProperties}
        >
          <div className="branding-preview__bar" style={{ background: 'var(--sw-primary)' }} />
          <div className="branding-preview__heading">Thridha Labs</div>
          <div
            className="branding-preview__muted"
            style={{ '--sw-muted': 'color-mix(in srgb, var(--sw-text) 66%, transparent)' } as React.CSSProperties}
          >
            Tagline or short descriptor rendered with secondary text.
          </div>
          <div
            className="branding-preview__actions"
            style={{ '--sw-action': 'var(--sw-accent)' } as React.CSSProperties}
          >
            <button
              type="button"
              className="branding-preview__button"
              style={{
                background: 'var(--sw-accent)',
                borderColor: 'color-mix(in srgb, var(--sw-text) 15%, transparent)',
                color: inkOn(colors.accent),
              }}
              tabIndex={-1}
            >
              Action
            </button>
            <span className="branding-preview__link" style={{ color: 'var(--sw-secondary)' }}>
              Secondary link
            </span>
          </div>
        </div>

        <div
          className="branding-preview__surface branding-preview__surface--raised"
          style={{ '--sw-surface': 'color-mix(in srgb, var(--sw-text) 9%, transparent)' } as React.CSSProperties}
        >
          <div className="branding-preview__row">
            <span className="branding-preview__label">Primary</span>
            <span className="branding-preview__chip">
              <span className="branding-preview__chip-dot" style={{ background: 'var(--sw-primary)' }} />
              {colors.primary}
            </span>
          </div>
          <div className="branding-preview__row">
            <span className="branding-preview__label">Secondary</span>
            <span className="branding-preview__chip">
              <span className="branding-preview__chip-dot" style={{ background: 'var(--sw-secondary)' }} />
              {colors.secondary}
            </span>
          </div>
          <div className="branding-preview__row">
            <span className="branding-preview__label">Accent</span>
            <span className="branding-preview__chip">
              <span className="branding-preview__chip-dot" style={{ background: 'var(--sw-accent)' }} />
              {colors.accent}
            </span>
          </div>
        </div>
      </div>
      <p className="admin-section__hint">
        Live preview — theme paints as {mode === 'dark' ? 'dark' : 'light'}, updated immediately on any change.
      </p>
    </div>
  )
}