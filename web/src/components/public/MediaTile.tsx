/**
 * MediaTile — public image slot for content (project thumbnails, galleries…).
 *
 * Renders real media through the public delivery route when a media id is
 * available. Falls back to the instrument-panel placeholder when no media id
 * exists or when the image cannot be loaded, so a broken asset never blanks
 * the page.
 */

import { useEffect, useRef, useState } from 'react'
import { resolveMediaUrl } from '../../lib/utils/mediaUrl'

export interface MediaTileProps {
  /** What this visual represents (project name, client name, …). */
  label: string
  mediaId?: string | null
  aspect?: 'wide' | 'square'
  large?: boolean
  /** Hide the visible caption (used when the name is repeated right below). */
  hideLabel?: boolean
  /** Variant to fetch from the public media route (defaults by size). */
  variant?: 'thumb' | 'md' | 'lg'
  /**
   * Preserve the whole image instead of cropping it to the tile frame.
   * Use for promotional artwork (activity banners) whose designed text, logos
   * and mockups must stay visible across the full width. Thumbnails keep the
   * default `cover` crop.
   */
  natural?: boolean
}

export function MediaTile({ label, mediaId, aspect = 'wide', large = false, hideLabel = false, variant, natural = false }: MediaTileProps) {
  const [failed, setFailed] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const imgRef = useRef<HTMLImageElement>(null)
  const registered = Boolean(mediaId)
  const src = !failed && mediaId ? resolveMediaUrl(mediaId, variant ?? (large ? 'lg' : 'md')) : null

  // Cached images may already be complete before the onLoad handler attaches.
  useEffect(() => {
    setLoaded(false)
    const el = imgRef.current
    if (el?.complete) setLoaded(true)
  }, [src])

  const classes = [
    'media-tile',
    aspect === 'square' ? 'media-tile--square' : '',
    large ? 'media-tile--large' : '',
    natural ? 'media-tile--natural' : '',
    natural && src && loaded ? 'is-loaded' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={classes}>
      {src ? (
        <img
          ref={imgRef}
          className="media-tile__img"
          src={src}
          alt={`${label} visual`}
          loading="lazy"
          decoding="async"
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
        />
      ) : (
        <span className="media-tile__sigil" aria-hidden="true" />
      )}
      {!hideLabel && <span className="media-tile__label">{label}</span>}
      {!src && registered && <span className="media-tile__note">Media registered</span>}
    </div>
  )
}