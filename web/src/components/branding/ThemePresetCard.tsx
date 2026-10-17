/**
 * ThemePresetCard — a selectable theme preset in the Branding designer.
 * Each card is a native radio control wrapped in a label, so the whole card
 * is clickable and keyboard-accessible. Selection feedback (check, border,
 * surface treatment) is visible without relying on color alone.
 */

import type { BrandingPreset } from '../../lib/utils/brandingPresets'
import { inkOn } from '../../lib/utils/brandingPresets'

export interface ThemePresetCardProps {
  preset: BrandingPreset
  groupName: string
  selected: boolean
  onSelect: (id: string) => void
}

export function ThemePresetCard({ preset, groupName, selected, onSelect }: ThemePresetCardProps) {
  const { colors, surfaces, mode } = preset

  return (
    <label
      className={`theme-card${selected ? ' theme-card--selected' : ''}`}
      data-mode={mode}
    >
      <input
        type="radio"
        name={groupName}
        value={preset.id}
        checked={selected}
        onChange={() => onSelect(preset.id)}
        className="theme-card__input"
        aria-label={`${preset.name} theme`}
      />
      <span className="theme-card__face" aria-hidden="true">
        <span
          className="theme-card__canvas"
          style={{
            background: colors.background,
            color: colors.text,
            borderColor: surfaces.border,
          }}
        >
          <span className="theme-card__nav" style={{ borderColor: surfaces.border }}>
            <span className="theme-card__nav-line" style={{ background: colors.primary }} />
            <span className="theme-card__nav-line theme-card__nav-line--ghost" style={{ background: colors.secondary }} />
          </span>
          <span className="theme-card__stage">
            <span
              className="theme-card__button theme-card__button--accent"
              style={{ background: colors.accent, color: inkOn(colors.accent) }}
            >
              Action
            </span>
            <span
              className="theme-card__mini-card"
              style={{ background: surfaces.surface, borderColor: surfaces.border }}
            >
              <span className="theme-card__mini-rule" style={{ background: colors.primary }} />
              <span className="theme-card__mini-text" style={{ color: colors.text }}>
                Sample
              </span>
              <span className="theme-card__mini-meta" style={{ color: surfaces.text2 }}>
                Card
              </span>
            </span>
          </span>
          {selected ? (
            <svg className="theme-card__check" viewBox="0 0 24 24" width="18" height="18" fill="none">
              <path
                d="M5 12.4 10 17.5 19 7"
                stroke="currentColor"
                strokeWidth="2.4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          ) : null}
        </span>
        <span className="theme-card__swatches">
          {[
            { key: 'primary', value: colors.primary, label: 'Primary' },
            { key: 'secondary', value: colors.secondary, label: 'Secondary' },
            { key: 'accent', value: colors.accent, label: 'Accent' },
            { key: 'text', value: colors.text, label: 'Text' },
          ].map((swatch) => (
            <span
              key={swatch.key}
              className={`theme-card__swatch theme-card__swatch--${swatch.key}`}
              style={{ background: swatch.value }}
              title={`${swatch.label} ${swatch.value}`}
            />
          ))}
        </span>
        <span className="theme-card__body">
          <span className="theme-card__name">{preset.name}</span>
          <span className="theme-card__desc">{preset.description}</span>
          <span className={`theme-card__mode theme-card__mode--${mode}`}>
            {mode === 'dark' ? 'Dark' : 'Light'}
          </span>
        </span>
      </span>
      <span className="visually-hidden">{preset.name}: {preset.description}</span>
    </label>
  )
}