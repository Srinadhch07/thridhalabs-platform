/**
 * ShareActions — canonical-URL sharing for public detail pages.
 *
 * Uses the native device share sheet when available, always offers "Copy
 * link" with success/failure feedback, and provides direct share targets
 * (X, LinkedIn, Facebook, WhatsApp, Email). Every action uses the canonical
 * public URL passed in — never an admin or internal URL.
 */

import { useState } from 'react'

interface ShareActionsProps {
  /** Canonical public URL of the page being shared. */
  url: string
  /** Human title used by the share sheet and direct-share text. */
  title: string
  /** Optional supporting text (e.g. the page description). */
  text?: string
  className?: string
}

type Status = 'idle' | 'copied' | 'error'

const _encoded = (value: string) => encodeURIComponent(value)

function directTargets(url: string, title: string) {
  const u = _encoded(url)
  const t = _encoded(title)
  return [
    { label: 'Share on X', short: 'X', href: `https://twitter.com/intent/tweet?url=${u}&text=${t}` },
    { label: 'Share on LinkedIn', short: 'in', href: `https://www.linkedin.com/sharing/share-offsite/?url=${u}` },
    { label: 'Share on Facebook', short: 'f', href: `https://www.facebook.com/sharer/sharer.php?u=${u}` },
    { label: 'Share on WhatsApp', short: 'wa', href: `https://wa.me/?text=${t}%20${u}` },
    { label: 'Share by email', short: '@', href: `mailto:?subject=${t}&body=${u}` },
  ]
}

export function ShareActions({ url, title, text, className }: ShareActionsProps) {
  const [status, setStatus] = useState<Status>('idle')

  const canNativeShare =
    typeof navigator !== 'undefined' && typeof navigator.share === 'function'

  async function handleNativeShare() {
    try {
      await navigator.share(text ? { title, text, url } : { title, url })
    } catch {
      // The user dismissed the sheet (AbortError) or sharing failed — the
      // copy/direct options below remain available.
    }
  }

  async function handleCopy() {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(url)
      } else {
        // Legacy fallback for browsers without the async clipboard API.
        const field = document.createElement('textarea')
        field.value = url
        field.setAttribute('readonly', '')
        field.style.position = 'fixed'
        field.style.opacity = '0'
        document.body.appendChild(field)
        field.select()
        const ok = document.execCommand('copy')
        document.body.removeChild(field)
        if (!ok) throw new Error('copy failed')
      }
      setStatus('copied')
    } catch {
      setStatus('error')
    }
  }

  const rootClass = className ? `share-actions ${className}` : 'share-actions'

  return (
    <section className={rootClass} aria-label="Share this page">
      <span className="eyebrow share-actions__label">Share</span>
      <div className="share-actions__group" role="group" aria-label="Share options">
        {canNativeShare ? (
          <button
            type="button"
            className="share-btn share-btn--primary"
            onClick={handleNativeShare}
          >
            Share
          </button>
        ) : null}
        <button type="button" className="share-btn" onClick={handleCopy}>
          Copy link
        </button>
        {directTargets(url, title).map((target) => (
          <a
            key={target.short}
            className="share-btn share-btn--icon"
            href={target.href}
            target="_blank"
            rel="noreferrer"
            aria-label={target.label}
            title={target.label}
          >
            {target.short}
          </a>
        ))}
      </div>
      <span className="share-actions__status" role="status" aria-live="polite">
        {status === 'copied' ? 'Link copied' : null}
        {status === 'error' ? "Couldn't copy — copy the address bar instead" : null}
      </span>
    </section>
  )
}
