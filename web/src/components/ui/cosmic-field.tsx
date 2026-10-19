/**
 * CosmicField — cinematic, theme-aware deep-space backdrop for the public hero.
 *
 * A hand-written <canvas> renderer (no WebGL/Three.js dependency). It composes
 * a layered cosmic scene that reads from the SAME runtime branding theme as the
 * rest of the site, so every predefined palette and custom admin color drives
 * it:
 *
 *   - two soft nebula washes (primary + secondary),
 *   - three parallax star layers (far → near),
 *   - drifting luminous dust motes,
 *   - faint orbital arcs / astronomical geometry,
 *   - a luminous focal core that anchors the composition.
 *
 * Performance & correctness:
 *   - one requestAnimationFrame loop, DPR-aware, re-created on resize,
 *   - paused when the tab is hidden (`visibilitychange`) or the hero is
 *     scrolled out of view (IntersectionObserver),
 *   - no React state in the frame loop (the canvas is imperative),
 *   - prefers-reduced-motion renders a single, still frame,
 *   - colors are re-read when the branding CSS variables change, so an admin
 *     theme switch (predefined or custom) is reflected live,
 *   - gracefully renders nothing (a plain themed gradient remains in CSS) if
 *     2D canvas is unavailable.
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
  twinklePhase: number
  twinkleSpeed: number
}

interface Dust {
  x: number
  y: number
  r: number
  vx: number
  vy: number
  alpha: number
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

    const reduced =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    let width = 0
    let height = 0
    let dpr = 1
    let stars: Star[] = []
    let dust: Dust[] = []
    let theme: Theme = readTheme(document.documentElement)

    const buildScene = (w: number, h: number) => {
      const area = w * h
      // Density scales with area but is capped so large monitors / mobile both
      // stay performant and natural.
      const farCount = Math.min(520, Math.round(area / 4200))
      const midCount = Math.min(260, Math.round(area / 9000))
      const nearCount = Math.min(90, Math.round(area / 26000))
      const dustCount = Math.min(90, Math.round(area / 24000))

      const rng = makeRng(0x9e3779b1)
      const makeLayer = (count: number, rMin: number, rMax: number, aMin: number, aMax: number): Star[] => {
        const out: Star[] = []
        for (let i = 0; i < count; i += 1) {
          out.push({
            x: rng(),
            y: rng(),
            r: rMin + rng() * (rMax - rMin),
            baseAlpha: aMin + rng() * (aMax - aMin),
            twinklePhase: rng() * Math.PI * 2,
            twinkleSpeed: 0.4 + rng() * 1.1,
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

      dust = []
      for (let i = 0; i < dustCount; i += 1) {
        dust.push({
          x: rng(),
          y: rng(),
          r: 0.6 + rng() * 1.8,
          vx: (rng() - 0.5) * 0.012,
          vy: -0.004 - rng() * 0.01,
          alpha: 0.06 + rng() * 0.16,
        })
      }
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

    const drawNebula = (time: number) => {
      const { primary, secondary, background, light } = theme
      // In dark themes the nebula glows against deep space; in light themes it
      // becomes a soft tint over the bright background (kept subtle so the
      // editorial text stays the hero). Alpha is theme-derived.
      const cloudA = light ? 0.16 : 0.34
      const cloudB = light ? 0.11 : 0.26

      const drift = reduced ? 0 : Math.sin(time * 0.00004) * 0.04
      const cx1 = width * (0.74 + drift)
      const cy1 = height * (0.34 + Math.cos(time * 0.00003) * 0.03)
      const radius1 = Math.max(width, height) * 0.62
      const g1 = ctx.createRadialGradient(cx1, cy1, 0, cx1, cy1, radius1)
      const p1 = mix(primary, background, light ? 0.45 : 0.16)
      g1.addColorStop(0, rgba(p1, cloudA))
      g1.addColorStop(0.45, rgba(mix(primary, background, 0.5), cloudA * 0.4))
      g1.addColorStop(1, rgba(background, 0))
      ctx.fillStyle = g1
      ctx.fillRect(0, 0, width, height)

      const cx2 = width * (0.18 - drift * 0.6)
      const cy2 = height * (0.78 + Math.sin(time * 0.00005) * 0.03)
      const radius2 = Math.max(width, height) * 0.5
      const g2 = ctx.createRadialGradient(cx2, cy2, 0, cx2, cy2, radius2)
      const p2 = mix(secondary, background, light ? 0.5 : 0.2)
      g2.addColorStop(0, rgba(p2, cloudB))
      g2.addColorStop(0.5, rgba(mix(secondary, background, 0.55), cloudB * 0.35))
      g2.addColorStop(1, rgba(background, 0))
      ctx.globalCompositeOperation = 'lighter'
      ctx.fillStyle = g2
      ctx.fillRect(0, 0, width, height)
      ctx.globalCompositeOperation = 'source-over'
    }

    const drawOrbits = (time: number) => {
      const { primary, secondary, light } = theme
      const cx = width * 0.74
      const cy = height * 0.36
      const baseAlpha = light ? 0.14 : 0.22
      const rings = [
        { rx: Math.min(width, height) * 0.30, ry: Math.min(width, height) * 0.17, rot: -0.5, color: primary },
        { rx: Math.min(width, height) * 0.44, ry: Math.min(width, height) * 0.24, rot: 0.35, color: primary },
        { rx: Math.min(width, height) * 0.58, ry: Math.min(width, height) * 0.30, rot: -0.15, color: secondary },
      ]
      ctx.save()
      ctx.lineWidth = 1
      for (let i = 0; i < rings.length; i += 1) {
        const ring = rings[i]
        ctx.beginPath()
        ctx.ellipse(cx, cy, ring.rx, ring.ry, ring.rot, 0, Math.PI * 2)
        ctx.strokeStyle = rgba(ring.color, baseAlpha * (1 - i * 0.18))
        ctx.stroke()
      }
      // A travelling node on the second ring.
      if (!reduced) {
        const angle = time * 0.00016
        const rx = rings[1].rx
        const ry = rings[1].ry
        const rot = rings[1].rot
        const px = cx + Math.cos(angle) * rx * Math.cos(rot) - Math.sin(angle) * ry * Math.sin(rot)
        const py = cy + Math.cos(angle) * rx * Math.sin(rot) + Math.sin(angle) * ry * Math.cos(rot)
        const glow = ctx.createRadialGradient(px, py, 0, px, py, 22)
        glow.addColorStop(0, rgba(theme.accent, 0.9))
        glow.addColorStop(1, rgba(theme.accent, 0))
        ctx.fillStyle = glow
        ctx.beginPath()
        ctx.arc(px, py, 22, 0, Math.PI * 2)
        ctx.fill()
      }
      ctx.restore()
    }

    const drawCore = (time: number) => {
      const { accent, primary, light } = theme
      const cx = width * 0.74
      const cy = height * 0.36
      const pulse = reduced ? 1 : 0.92 + Math.sin(time * 0.0006) * 0.08
      const radius = Math.min(width, height) * 0.5 * pulse
      const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius)
      g.addColorStop(0, rgba(mix(accent, { r: 255, g: 255, b: 255 }, 0.35), light ? 0.5 : 0.85))
      g.addColorStop(0.08, rgba(accent, light ? 0.32 : 0.55))
      g.addColorStop(0.32, rgba(primary, light ? 0.12 : 0.22))
      g.addColorStop(1, rgba(primary, 0))
      ctx.globalCompositeOperation = 'lighter'
      ctx.fillStyle = g
      ctx.beginPath()
      ctx.arc(cx, cy, radius, 0, Math.PI * 2)
      ctx.fill()
      ctx.globalCompositeOperation = 'source-over'
    }

    const drawStars = (time: number) => {
      const { text, background, light } = theme
      // Stars read as light text-hued points; on light themes they darken so
      // they remain visible without turning the scene muddy.
      const starColor = light ? mix(background, { r: 0, g: 0, b: 0 }, 0.35) : mix(text, { r: 255, g: 255, b: 255 }, 0.2)
      for (let i = 0; i < stars.length; i += 1) {
        const star = stars[i]
        const twinkle = reduced ? 1 : 0.6 + 0.4 * Math.sin(time * 0.001 * star.twinkleSpeed + star.twinklePhase)
        ctx.fillStyle = rgba(starColor, star.baseAlpha * twinkle)
        const px = star.x * width
        const py = star.y * height
        ctx.beginPath()
        ctx.arc(px, py, star.r, 0, Math.PI * 2)
        ctx.fill()
      }
    }

    const drawDust = (delta: number) => {
      const { accent, primary, light } = theme
      for (let i = 0; i < dust.length; i += 1) {
        const d = dust[i]
        if (!reduced) {
          d.x += d.vx * delta * 0.06
          d.y += d.vy * delta * 0.06
          if (d.y < -0.05) d.y = 1.05
          if (d.x < -0.05) d.x = 1.05
          if (d.x > 1.05) d.x = -0.05
        }
        ctx.fillStyle = rgba(i % 2 === 0 ? accent : primary, d.alpha * (light ? 0.7 : 1))
        ctx.beginPath()
        ctx.arc(d.x * width, d.y * height, d.r, 0, Math.PI * 2)
        ctx.fill()
      }
    }

    const render = (time: number, delta = 16) => {
      ctx.clearRect(0, 0, width, height)
      drawNebula(time)
      drawStars(time)
      drawOrbits(time)
      drawCore(time)
      drawDust(delta)
    }

    resize()

    let rafId = 0
    let last = 0
    let running = false
    let visible = true

    const frame = (time: number) => {
      const delta = last ? Math.min(48, time - last) : 16
      last = time
      render(time, delta)
      rafId = requestAnimationFrame(frame)
    }

    const start = () => {
      if (running || reduced) return
      running = true
      last = 0
      rafId = requestAnimationFrame(frame)
    }
    const stop = () => {
      running = false
      if (rafId) cancelAnimationFrame(rafId)
      rafId = 0
    }

    if (reduced) {
      render(0)
    } else {
      start()
    }

    const onResize = () => {
      resize()
      if (reduced) render(0)
    }
    window.addEventListener('resize', onResize)

    const onVisibility = () => {
      visible = document.visibilityState === 'visible'
      if (!reduced && visible) start()
      else stop()
    }
    document.addEventListener('visibilitychange', onVisibility)

    // Re-read theme colors whenever the branding variables are re-applied.
    const observer = new MutationObserver(() => {
      theme = readTheme(document.documentElement)
      if (reduced) render(0)
    })
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['style'] })

    // Stop the loop while the hero is off-screen.
    let intersection: IntersectionObserver | null = null
    if (typeof IntersectionObserver !== 'undefined') {
      intersection = new IntersectionObserver(
        (entries) => {
          const entry = entries[0]
          if (!reduced && entry.isIntersecting && visible) start()
          else if (!entry.isIntersecting) stop()
        },
        { threshold: 0 },
      )
      intersection.observe(canvas)
    }

    return () => {
      stop()
      window.removeEventListener('resize', onResize)
      document.removeEventListener('visibilitychange', onVisibility)
      observer.disconnect()
      intersection?.disconnect()
    }
  }, [])

  return (
    <div className={`cosmic-field${className ? ` ${className}` : ''}`} aria-hidden="true">
      <canvas ref={canvasRef} className="cosmic-field__canvas" />
    </div>
  )
}
