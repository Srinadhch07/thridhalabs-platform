/**
 * CertifiedWorkSection — the work behind a verified certificate.
 *
 * Renders the *certified snapshot*: the exact version Thridha Labs reviewed and
 * approved. It is never the work's current state, so later edits cannot rewrite
 * what was certified. Only rendered when the backend confirms the work is still
 * publicly showable; if the work has since been edited, a clearly labelled link
 * to the current version is offered separately.
 */

import { ContentRenderer } from '../works/ContentRenderer'
import { MediaTile } from '../public/MediaTile'
import { TechChips } from '../public/TechChips'
import { MemberAvatar } from '../member/MemberAvatar'
import type { PublicCertificateWork } from '../../types/certificate'

function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
}

export function CertifiedWorkSection({ work }: { work: PublicCertificateWork }) {
  return (
    <section className="cert-work" aria-labelledby="cert-work-heading">
      <div className="cert-work__head">
        <p className="eyebrow">
          <span className="hud-dot" aria-hidden="true" /> The work behind this certificate
        </p>
        <span className="chip cert-work__badge">Certified version</span>
      </div>

      <h2 id="cert-work-heading" className="cert-work__title">
        {work.title}
      </h2>
      {work.summary ? <p className="cert-work__summary">{work.summary}</p> : null}

      <div className="cert-work__byline">
        <MemberAvatar
          name={work.author.display_name}
          mediaId={work.author.picture_media_id}
          size="sm"
        />
        <span>
          {work.member_profile_url ? (
            <a href={work.member_profile_url}>{work.author.display_name}</a>
          ) : (
            work.author.display_name
          )}
          {work.certified_at ? ` · Certified ${formatDate(work.certified_at)}` : ''}
        </span>
      </div>

      {work.tags.length > 0 ? <TechChips items={work.tags} /> : null}

      {work.cover_media_id ? (
        <div className="cert-work__cover">
          <MediaTile label={work.title} mediaId={work.cover_media_id} large />
        </div>
      ) : null}

      <ContentRenderer document={work.content} />

      {work.external_links.length > 0 ? (
        <section className="work-public__links" aria-label="External links">
          <h3 className="work-heading">Links</h3>
          <ul className="work-public__link-list">
            {work.external_links.map((link) => (
              <li key={link.url}>
                <a href={link.url} target="_blank" rel="noreferrer">
                  {link.label} <span aria-hidden="true">↗</span>
                </a>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {work.current_work_url ? (
        <div className="cert-work__actions">
          {work.has_newer_version ? (
            <p className="cert-work__version-note" role="status">
              This work has been updated since it was certified. The presentation above is the
              certified version that was reviewed.
            </p>
          ) : null}
          <a
            className="btn btn--ghost"
            href={work.current_work_url}
            target="_blank"
            rel="noreferrer"
          >
            {work.has_newer_version ? 'View the current version' : 'View full project'}{' '}
            <span aria-hidden="true">↗</span>
          </a>
        </div>
      ) : null}
    </section>
  )
}
