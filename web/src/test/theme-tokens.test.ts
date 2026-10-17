/** Theme token mapping guard.
 *
 * The base surface/text/border palette must stay DERIVED from the five
 * brandable --color-* tokens so every admin, member and public surface
 * follows the selected branding theme. These tests fail if a dark-only color
 * is baked back into tokens.css, or a hard-coded accent is reintroduced for
 * text selection. */

import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { BRANDING_PRESETS, inkOn } from '../lib/utils/brandingPresets'

function readStylesheet(file: string): string {
  return readFileSync(path.join(process.cwd(), 'src', 'styles', file), 'utf8')
}

const tokensCss = readStylesheet('tokens.css')
const globalsCss = readStylesheet('globals.css')

const DERIVED_TOKENS = ['--bg', '--bg-2', '--bg-3', '--ink', '--ink-dim', '--muted', '--faint', '--line', '--line-2', '--gridline']

describe('theme token mapping', () => {
  it('keeps concrete fallback values for the five brandable tokens', () => {
    expect(tokensCss).toContain('--color-primary: var(--amber);')
    expect(tokensCss).toContain('--color-secondary: var(--teal);')
    expect(tokensCss).toContain('--color-accent: var(--amber-hi);')
    expect(tokensCss).toContain('--color-background: #070910;')
    expect(tokensCss).toContain('--color-text: #e9edf5;')
  })

  it('derives every base surface/text/border token from the brand pair', () => {
    for (const token of DERIVED_TOKENS) {
      expect(tokensCss).toMatch(new RegExp(`${token}:`))
    }
    expect(tokensCss).toMatch(/--bg:\s*var\(--color-background\);/)
    expect(tokensCss).toMatch(/--ink:\s*var\(--color-text\);/)

    const palette = tokensCss.slice(0, tokensCss.indexOf('--- status ---'))
    for (const token of ['--bg-2', '--bg-3', '--ink-dim', '--muted', '--faint', '--line', '--line-2', '--gridline']) {
      const line = palette.split('\n').find((entry) => entry.startsWith(`  ${token}:`))
      expect(line).toBeTruthy()
      expect(line).toMatch(/var\(--color-text\)|var\(--color-background\)/)
    }

    // the old hard-coded dark hairlines must not resurface
    expect(tokensCss).not.toMatch(/rgba\(190, 208, 232/)
  })

  it('keeps the semantic status colors independent of the theme', () => {
    expect(tokensCss).toMatch(/--ok: #5fd0c0;/)
    expect(tokensCss).toMatch(/--warn: #f2ad63;/)
    expect(tokensCss).toMatch(/--err: #e05a4a;/)
  })

  it('switches accent ink per color scheme with a dark fallback', () => {
    expect(tokensCss).toMatch(/--on-accent: #14100a;/)
    expect(tokensCss).toMatch(/@supports \(color: light-dark\(#000, #fff\)\)/)
    expect(tokensCss).toMatch(/--on-accent: light-dark\(#ffffff, #14100a\);/)
  })

  it('keeps text selection theme-aware rather than accent-colored', () => {
    const selection = globalsCss.slice(globalsCss.indexOf('::selection'), globalsCss.indexOf(':focus-visible'))
    expect(selection).toMatch(/var\(--color-text\) 18%, transparent/)
    expect(selection).not.toMatch(/var\(--accent\)/)
    expect(selection).toMatch(/color: var\(--color-text\);/)
  })
})

describe('inkOn (CSS --on-accent parity)', () => {
  it('matches the CSS rule for every preset: dark ink on pale accents, light ink on deep accents', () => {
    for (const preset of BRANDING_PRESETS) {
      expect(inkOn(preset.colors.accent)).toBe(preset.mode === 'dark' ? '#14100a' : '#ffffff')
    }
  })

  it('handles custom values and invalid input gracefully', () => {
    expect(inkOn('#1d4ed8')).toBe('#ffffff')
    expect(inkOn('#ffd7a6')).toBe('#14100a')
    expect(inkOn('garbage')).toBe('#14100a')
    expect(inkOn('#fff')).toBe('#14100a')
  })
})