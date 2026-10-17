/**
 * ClientTile — client card: monogram mark, industry, description and a link
 * out to their site when one is configured.
 */

import type { PublicClient } from '../../types/content'
import { resolveMediaUrl } from '../../lib/utils/mediaUrl'
import { initialsOf } from './labels'

export interface ClientTileProps {
  client: PublicClient
}

export function ClientTile({ client }: ClientTileProps) {
  const projectCount = client.projects.length
  const logo = resolveMediaUrl(client.logo_media_id, 'thumb')
  const cover = resolveMediaUrl(client.featured_image_media_id, 'md')
  return (
    <article className="client-tile">
      {cover && (
        <img
          className="client-tile__cover"
          src={cover}
          alt={`${client.name} featured visual`}
          loading="lazy"
          decoding="async"
        />
      )}
      {logo ? (
        <img
          className="client-tile__monogram"
          src={logo}
          alt={`${client.name} logo`}
          loading="lazy"
          decoding="async"
        />
      ) : (
        <span className="client-tile__monogram" aria-hidden="true">
          {initialsOf(client.name)}
        </span>
      )}
      <h3>{client.name}</h3>
      {(client.industry || client.category) && (
        <p className="client-tile__industry">{client.industry || client.category}</p>
      )}
      {client.description && <p className="client-tile__desc">{client.description}</p>}
      <div className="client-tile__foot">
        {client.website ? (
          <a href={client.website} target="_blank" rel="noreferrer">
            Website <span aria-hidden="true">↗</span>
          </a>
        ) : null}
        <span className="client-tile__count">
          {projectCount} {projectCount === 1 ? 'project' : 'projects'}
        </span>
      </div>
    </article>
  )
}