/**
 * CosmicField — restrained, theme-aware backdrop for the public hero.
 *
 * A hand-written <canvas> renderer (no WebGL/Three.js dependency) that paints a
 * single, still deep-space composition reading from the SAME runtime branding
 * theme as the rest of the site:
 *
 *   - one soft nebula wash (primary) and one secondary tint,
 *   - a sparse field of static star points.
 *
 * It is deliberately static: no animation loop, drifting dust, travelling
 * nodes, pulsing core or twinkling stars — the backdrop must never compete with
 * the editorial content. It renders once on mount and again on resize or when
 * the branding variables change (so an admin theme switch is reflected live).
 */

import { useEffect, useRef } from 'react'

interface CosmicFieldProps {
  className?: string
}

interface Star {
  x: number
  y: number
  r: number
  baseAlpha: number
}

interface Rgb {
  r: number
  g: number
  b: number
}

/** Deterministic PRNG so the field is stable across renders/resizes. */
function makeRng(seed: number): () => number {
  let value = seed >>> 0
  return () => {
    value = (value * 1664525 + 1013904223) >>> 0
    return value / 4294967296
  }
}

function parseColor(input: string): Rgb | null {
  const probe = input.trim()
  if (!probe) return null
  // Hex forms.
  const hex = probe.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i)
  if (hex) {
    let body = hex[1]
    if (body.length === 3) body = body.split('').map((c) => c + c).join('')
    return {
      r: parseInt(body.slice(0, 2), 16),
      g: parseInt(body.slice(2, 4), 16),
      b: parseInt(body.slice(4, 6), 16),
    }
  }
  // rgb()/rgba() forms (getComputedStyle often normalizes to these).
  const rgb = probe.match(/^rgba?\(([^)]+)\)$/i)
  if (rgb) {
    const parts = rgb[1].split(/[,\s/]+/).filter(Boolean)
    if (parts.length >= 3) {
      return {
        r: Number(parts[0]),
        g: Number(parts[1]),
        b: Number(parts[2]),
      }
    }
  }
  return null
}

function rgba(color: Rgb, alpha: number): string {
  return `rgba(${color.r}, ${color.g}, ${color.b}, ${alpha})`
}

function mix(a: Rgb, b: Rgb, t: number): Rgb {
  return {
    r: Math.round(a.r + (b.r - a.r) * t),
    g: Math.round(a.g + (b.g - a.g) * t),
    b: Math.round(a.b + (b.b - a.b) * t),
  }
}

/** Relative luminance — used to tune the scene for light vs dark themes. */
function luminance(color: Rgb): number {
  const channel = (c: number) => {
    const v = c / 255
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)
  }
  return 0.2126 * channel(color.r) + 0.7152 * channel(color.g) + 0.0722 * channel(color.b)
}

interface Theme {
  primary: Rgb
  secondary: Rgb
  accent: Rgb
  background: Rgb
  text: Rgb
  /** True when the active theme is light (bright background). */
  light: boolean
}

function readTheme(el: Element): Theme {
  const styles = getComputedStyle(el)
  const fallback: Rgb = { r: 242, g: 173, b: 99 }
  const primary = parseColor(styles.getPropertyValue('--color-primary')) ?? fallback
  const secondary = parseColor(styles.getPropertyValue('--color-secondary')) ?? fallback
  const accent = parseColor(styles.getPropertyValue('--color-accent')) ?? primary
  const background = parseColor(styles.getPropertyValue('--color-background')) ?? { r: 7, g: 9, b: 16 }
  const text = parseColor(styles.getPropertyValue('--color-text')) ?? { r: 233, g: 237, b: 245 }
  return { primary, secondary, accent, background, text, light: luminance(background) > 0.45 }
}

export function CosmicField({ className }: CosmicFieldProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    let width = 0
    let height = 0
    let dpr = 1
    let stars: Star[] = []
    let theme: Theme = readTheme(document.documentElement)

    let animationId = 0
    let time = 0

    const buildScene = (w: number, h: number) => {
      const area = w * h
      // Density scales with area but is capped so large monitors / mobile both
      // stay performant and natural.
      const farCount = Math.min(520, Math.round(area / 4200))
      const midCount = Math.min(260, Math.round(area / 9000))
      const nearCount = Math.min(90, Math.round(area / 26000))

      const rng = makeRng(0x9e3779b1)
      const makeLayer = (count: number, rMin: number, rMax: number, aMin: number, aMax: number): Star[] => {
        const out: Star[] = []
        for (let i = 0; i < count; i += 1) {
          out.push({
            x: rng(),
            y: rng(),
            r: rMin + rng() * (rMax - rMin),
            baseAlpha: aMin + rng() * (aMax - aMin),
          })
        }
        return out
      }

      // Far layer is the densest/dimmest; near layer sparse/brightest.
      stars = [
        ...makeLayer(farCount, 0.3, 0.7, 0.18, 0.42),
        ...makeLayer(midCount, 0.5, 1.05, 0.3, 0.6),
        ...makeLayer(nearCount, 0.8, 1.7, 0.5, 0.95),
      ]
    }

    const resize = () => {
      const rect = canvas.getBoundingClientRect()
      width = Math.max(1, rect.width)
      height = Math.max(1, rect.height)
      dpr = Math.min(2, window.devicePixelRatio || 1)
      canvas.width = Math.round(width * dpr)
      canvas.height = Math.round(height * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      buildScene(width, height)
    }

    const drawNebula = () => {
      const { primary, secondary, background, light } = theme
      // A single, still themed wash so the dark-brand backdrop survives without
      // the previous animated nebula. Kept subtle so editorial text stays hero.
      const cloudA = light ? 0.12 : 0.2

      const cx1 = width * 0.74
      const cy1 = height * 0.34
      const radius1 = Math.max(width, height) * 0.62
      const g1 = ctx.createRadialGradient(cx1, cy1, 0, cx1, cy1, radius1)
      const p1 = mix(primary, background, light ? 0.45 : 0.16)
      g1.addColorStop(0, rgba(p1, cloudA))
      g1.addColorStop(0.45, rgba(mix(primary, background, 0.5), cloudA * 0.4))
      g1.addColorStop(1, rgba(background, 0))
      ctx.fillStyle = g1
      ctx.fillRect(0, 0, width, height)

      const cx2 = width * 0.18
      const cy2 = height * 0.78
      const radius2 = Math.max(width, height) * 0.5
      const g2 = ctx.createRadialGradient(cx2, cy2, 0, cx2, cy2, radius2)
      const p2 = mix(secondary, background, light ? 0.5 : 0.2)
      g2.addColorStop(0, rgba(p2, cloudA * 0.7))
      g2.addColorStop(0.5, rgba(mix(secondary, background, 0.55), cloudA * 0.25))
      g2.addColorStop(1, rgba(background, 0))
      ctx.fillStyle = g2
      ctx.fillRect(0, 0, width, height)
    }

    const drawStars = () => {
      const { text, background, light } = theme
      // Stars read as light text-hued points; on light themes they darken so
      // they remain visible without turning the scene muddy.
      const starColor = light ? mix(background, { r: 0, g: 0, b: 0 }, 0.35) : mix(text, { r: 255, g: 255, b: 255 }, 0.2)
      for (let i = 0; i < stars.length; i += 1) {
        const star = stars[i]
        const twinkle = reduceMotion ? 1 : 0.85 + Math.sin(time * 0.0008 + i * 0.37) * 0.12
        ctx.fillStyle = rgba(starColor, star.baseAlpha * 0.7 * twinkle)
        const px = star.x * width
        const py = star.y * height
        ctx.beginPath()
        ctx.arc(px, py, star.r, 0, Math.PI * 2)
        ctx.fill()
      }
    }

    const render = () => {
      ctx.clearRect(0, 0, width, height)
      drawNebula()
      drawStars()
    }

    const animate = () => {
      if (reduceMotion) {
        render()
        return
      }
      time += 16
      render()
      animationId = window.requestAnimationFrame(animate)
    }

    resize()
    if (reduceMotion) {
      render()
    } else {
      animate()
    }

    const onResize = () => {
      resize()
      render()
    }
    window.addEventListener('resize', onResize)

    // Re-read theme colors whenever the branding variables are re-applied.
    const observer = new MutationObserver(() => {
      theme = readTheme(document.documentElement)
      if (reduceMotion) {
        render()
      }
    })
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['style'] })

    return () => {
      window.removeEventListener('resize', onResize)
      observer.disconnect()
      if (!reduceMotion && animationId) {
        window.cancelAnimationFrame(animationId)
      }
    }
  }, [])

  return (
    <div className={`cosmic-field${className ? ` ${className}` : ''}`} aria-hidden="true">
      <canvas ref={canvasRef} className="cosmic-field__canvas" />
    </div>
  )
}
