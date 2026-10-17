/** CertificationSnapshotView — read-only rendering of a frozen work snapshot. */

import { ContentRenderer } from '../works/ContentRenderer'
import { MediaTile } from '../public/MediaTile'
import type { CertificationSnapshot } from '../../types/certification'

export function CertificationSnapshotView({ snapshot }: { snapshot: CertificationSnapshot }) {
  return (
    <div className="cert-snapshot">
      <h3 className="cert-snapshot__title">{snapshot.title}</h3>
      <p className="cert-snapshot__summary">{snapshot.summary}</p>
      {snapshot.tags.length > 0 ? (
        <p className="tech-chips" aria-label="Tags">
          {snapshot.tags.map((tag) => (
            <span className="chip" key={tag}>
              {tag}
            </span>
          ))}
        </p>
      ) : null}
      {snapshot.cover_media_id ? (
        <div className="cert-snapshot__cover">
          <MediaTile label={snapshot.title} mediaId={snapshot.cover_media_id} />
        </div>
      ) : null}
      <ContentRenderer document={snapshot.content} />
      {snapshot.external_links.length > 0 ? (
        <ul className="work-public__link-list">
          {snapshot.external_links.map((link) => (
            <li key={link.url}>
              <a href={link.url} target="_blank" rel="noreferrer">
                {link.label} <span aria-hidden="true">↗</span>
              </a>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
