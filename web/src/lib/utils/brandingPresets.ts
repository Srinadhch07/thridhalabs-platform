/**
 * Branding theme presets — six professionally coordinated color themes.
 *
 * The persisted branding schema stores five colors (`primary`, `secondary`,
 * `accent`, `background`, `text`) plus a mode. A preset maps its full
 * illustrative palette (extra neutral surfaces/border shown here) onto those
 * five stored fields so no parallel color system is introduced. The `surfaces`
 * block is used for theme-card artwork and documentation only; the real site
 * keeps blending its surfaces from the five stored variables exactly as the
 * design tokens do.
 *
 * Accent values are chosen for legibility: deeper variants on light themes,
 * brighter variants on dark themes — the existing buttons render dark ink on
 * the accent surface (`--on-accent`).
 */

import type { BrandingColors, BrandingMode } from '../../types/branding'

export const BRANDING_THEME_PRESET_IDS = [
  'arctic_white',
  'ivory_indigo',
  'pearl_emerald',
  'midnight_slate',
  'obsidian_violet',
  'graphite_amber',
] as const

export type BrandingThemePresetId = (typeof BRANDING_THEME_PRESET_IDS)[number]

/** Neutral palette details used to illustrate a theme card. */
export interface BrandingPresetSurfaces {
  /** Card / section surface. */
  surface: string
  /** Nested / elevated surface. */
  surface2: string
  /** Secondary text. */
  text2: string
  /** Hairline borders. */
  border: string
}

export interface BrandingPreset {
  id: BrandingThemePresetId
  name: string
  description: string
  mode: BrandingMode
  /** The five values persisted through the existing branding schema. */
  colors: BrandingColors
  /** Illustrative neutrals for the theme card artwork. */
  surfaces: BrandingPresetSurfaces
}

export const BRANDING_PRESETS: BrandingPreset[] = [
  {
    id: 'arctic_white',
    name: 'Arctic White',
    description: 'Clean, bright, minimal and premium',
    mode: 'light',
    colors: {
      primary: '#2563eb',
      secondary: '#0e7490',
      accent: '#1d4ed8',
      background: '#ffffff',
      text: '#0f172a',
    },
    surfaces: {
      surface: '#f8fafc',
      surface2: '#f1f5f9',
      text2: '#475569',
      border: '#e2e8f0',
    },
  },
  {
    id: 'ivory_indigo',
    name: 'Ivory & Indigo',
    description: 'Refined, modern and professional',
    mode: 'light',
    colors: {
      primary: '#4f46e5',
      secondary: '#7c3aed',
      accent: '#4338ca',
      background: '#ffffff',
      text: '#19172e',
    },
    surfaces: {
      surface: '#f8f7ff',
      surface2: '#f0eeff',
      text2: '#625e7d',
      border: '#e4e1f0',
    },
  },
  {
    id: 'pearl_emerald',
    name: 'Pearl & Emerald',
    description: 'Calm, fresh and trustworthy',
    mode: 'light',
    colors: {
      primary: '#059669',
      secondary: '#0f766e',
      accent: '#047857',
      background: '#ffffff',
      text: '#142a20',
    },
    surfaces: {
      surface: '#f7fbf9',
      surface2: '#eaf5ef',
      text2: '#52685c',
      border: '#dce9e1',
    },
  },
  {
    id: 'midnight_slate',
    name: 'Midnight Slate',
    description: 'A professional dark workspace',
    mode: 'dark',
    colors: {
      primary: '#60a5fa',
      secondary: '#2dd4bf',
      accent: '#93c5fd',
      background: '#0f172a',
      text: '#f8fafc',
    },
    surfaces: {
      surface: '#172033',
      surface2: '#1e293b',
      text2: '#cbd5e1',
      border: '#334155',
    },
  },
  {
    id: 'obsidian_violet',
    name: 'Obsidian & Violet',
    description: 'Modern, technical and premium',
    mode: 'dark',
    colors: {
      primary: '#a78bfa',
      secondary: '#e879f9',
      accent: '#c4b5fd',
      background: '#111014',
      text: '#faf7ff',
    },
    surfaces: {
      surface: '#1a1820',
      surface2: '#25212e',
      text2: '#c8c0d3',
      border: '#393343',
    },
  },
  {
    id: 'graphite_amber',
    name: 'Graphite & Amber',
    description: 'Technology lab, warm and confident',
    mode: 'dark',
    colors: {
      primary: '#f2ad63',
      secondary: '#5fd0c0',
      accent: '#ffd7a6',
      background: '#111315',
      text: '#f5f5f4',
    },
    surfaces: {
      surface: '#1a1d20',
      surface2: '#24282c',
      text2: '#c4c7c5',
      border: '#383d40',
    },
  },
]

export function isBrandingThemePresetId(value: string | null | undefined): value is BrandingThemePresetId {
  return typeof value === 'string' && (BRANDING_THEME_PRESET_IDS as readonly string[]).includes(value)
}

export function getBrandingPreset(id: string | null | undefined): BrandingPreset | null {
  if (!isBrandingThemePresetId(id)) return null
  return BRANDING_PRESETS.find((preset) => preset.id === id) ?? null
}

/** Exact color+mode match against the preset catalog (customized values won't match). */
export function findBrandingPreset(colors: BrandingColors, mode: BrandingMode): BrandingPreset | null {
  return BRANDING_PRESETS.find(
    (preset) => preset.mode === mode && presetColorsEqual(preset.colors, colors),
  ) ?? null
}

export function presetColorsEqual(a: BrandingColors, b: BrandingColors): boolean {
  return (
    a.primary.toLowerCase() === b.primary.toLowerCase() &&
    a.secondary.toLowerCase() === b.secondary.toLowerCase() &&
    a.accent.toLowerCase() === b.accent.toLowerCase() &&
    a.background.toLowerCase() === b.background.toLowerCase() &&
    a.text.toLowerCase() === b.text.toLowerCase()
  )
}

/** Choose light or dark ink for a given accent surface, mirroring the CSS
 *  `--on-accent` token (dark ink on the pale accents used by dark presets,
 *  light ink on the deep accents used by light presets). Uses the WCAG
 *  relative luminance of a #rrggbb hex background. */
export function inkOn(background: string): '#ffffff' | '#14100a' {
  const hex = background.replace(/^#/, '')
  if (!/^[0-9a-fA-F]{6}$/.test(hex)) return '#14100a'
  const channel = (start: number) => parseInt(hex.slice(start, start + 2), 16) / 255
  const linear = (c: number) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4))
  const luminance = 0.2126 * linear(channel(0)) + 0.7152 * linear(channel(2)) + 0.0722 * linear(channel(4))
  return luminance >= 0.45 ? '#14100a' : '#ffffff'
}