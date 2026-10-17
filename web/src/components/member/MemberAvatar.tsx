/**
 * MemberAvatar — the member's picture when one is set, otherwise their
 * initials. Derives its media URL through `resolveMediaUrl` so media routing
 * stays in one place.
 */

import { resolveMediaUrl } from '../../lib/utils/mediaUrl'

type AvatarSize = 'sm' | 'md' | 'lg' | 'xl'

interface MemberAvatarProps {
  name?: string | null
  mediaId?: string | null
  alt?: string
  size?: AvatarSize
  accent?: boolean
  className?: string
}

function initials(name?: string | null): string {
  if (!name) return '?'
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
}

export function MemberAvatar({
  name,
  mediaId,
  alt,
  size = 'md',
  accent,
  className = '',
}: MemberAvatarProps) {
  const url = mediaId ? resolveMediaUrl(mediaId, 'thumb') : null
  const label = alt ?? name?.trim() ?? 'Member'
  const classes = `member-avatar member-avatar--${size}${accent ? ' member-avatar--accent' : ''}${
    className ? ` ${className}` : ''
  }`

  if (url) {
    return (
      <span className={classes}>
        <img src={url} alt={label} loading="lazy" />
      </span>
    )
  }

  return (
    <span className={classes} role="img" aria-label={label}>
      {initials(name)}
    </span>
  )
}
