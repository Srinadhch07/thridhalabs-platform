/**
 * BackgroundPaths — atmospheric animated SVG backdrop for the public hero.
 *
 * Adapted from the supplied 21st.dev-style component to fit the Thridha Labs
 * design system rather than the shadcn/Tailwind defaults it shipped with:
 *
 * - No Tailwind, no shadcn `Button`, no `min-h-screen` takeover. This is a
 *   purely decorative, absolutely-positioned layer that fills its parent
 *   (the hero) and never dictates layout.
 * - Colors come from the runtime branding theme via CSS custom properties
 *   (`--color-primary`, `--color-secondary`, `--color-background`,
 *   `--color-text`), so the paths follow whatever palette (predefined or
 *   custom) the owner configured in the admin panel. Nothing is hard-coded.
 * - Stroke animation durations are deterministic per path index instead of
 *   `Math.random()` on every render, so animation is stable across re-renders
 *   and there are no layout/thrash surprises.
 * - `aria-hidden` + `pointer-events: none`: the layer never blocks pointer
 *   events, text selection, keyboard navigation or CTA interaction.
 * - `prefers-reduced-motion` renders the paths statically (no continuous
 *   animation), keeping a still, legible composition.
 */

import { motion, useReducedMotion } from 'framer-motion'

interface BackgroundPathsProps {
  className?: string
}

/** Deterministic, evenly-spaced vertical guides across the hero. */
const PATHS = [
  'M-140 480C 80 480 190 380 300 300S 520 140 740 140 1080 220 1320 120',
  'M-120 560C 120 560 240 470 360 380S 600 220 820 220 1120 300 1360 200',
  'M-160 400C 60 400 180 300 300 240S 540 60 760 60 1100 160 1340 60',
]

export function BackgroundPaths({ className }: BackgroundPathsProps) {
  const reduceMotion = useReducedMotion()

  return (
    <div
      className={`background-paths${className ? ` ${className}` : ''}`}
      aria-hidden="true"
    >
      <svg
        className="background-paths__svg"
        viewBox="0 0 1200 600"
        preserveAspectRatio="xMidYMid slice"
        focusable="false"
      >
        {PATHS.map((d, index) => {
          // Deterministic durations: slow, drifting, never synced.
          const duration = 24 + index * 6
          const delay = index * 1.6
          return (
            <motion.path
              key={d}
              d={d}
              className={
                index % 2 === 0 ? 'background-paths__stroke' : 'background-paths__stroke is-soft'
              }
              strokeWidth={index === 0 ? 1.5 : 1}
              initial={reduceMotion ? { pathLength: 1, opacity: 0.5 } : { pathLength: 0, opacity: 0 }}
              animate={
                reduceMotion
                  ? { pathLength: 1, opacity: 0.5 }
                  : {
                      pathLength: [0.05, 1, 1, 0.05],
                      opacity: [0, 0.85, 0.85, 0],
                    }
              }
              transition={
                reduceMotion
                  ? { duration: 0 }
                  : {
                      duration,
                      delay,
                      repeat: Infinity,
                      ease: 'easeInOut',
                    }
              }
            />
          )
        })}
      </svg>
    </div>
  )
}
