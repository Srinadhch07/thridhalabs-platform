/**
 * useJsonLd — inject deduplicated JSON-LD <script> blocks into <head>.
 *
 * Payloads are produced exclusively from JSON.stringify of structured data
 * authored here (no arbitrary database HTML), and React-free DOM injection
 * uses textContent, so no live user content is ever parsed as HTML.
 */

import { useEffect } from 'react'

export function useJsonLd(blocks: ReadonlyArray<Record<string, unknown> | null | undefined>): void {
  const key = JSON.stringify(blocks)
  useEffect(() => {
    if (typeof document === 'undefined') return
    const parsed: Array<Record<string, unknown>> = JSON.parse(key)
    const scripts: HTMLScriptElement[] = []
    for (const block of parsed) {
      if (!block) continue
      const el = document.createElement('script')
      el.type = 'application/ld+json'
      el.dataset.jsonLd = 'true'
      el.textContent = JSON.stringify(block)
      document.head.appendChild(el)
      scripts.push(el)
    }
    return () => {
      for (const el of scripts) el.remove()
    }
  }, [key])
}