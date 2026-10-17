/** WorkCard — a member work shown in the showcase list.
 *
 * The card body links to the work editor; an eligibility-gated certification
 * action sits *outside* that link so clicking it never triggers the card's
 * navigation and can deep-link straight to the editor's certification section.
 */

import { Link } from 'react-router-dom'
import { MediaTile } from '../public/MediaTile'
import { WORK_STATUS_CHIP, WORK_STATUS_LABELS, WORK_VISIBILITY_CHIP, WORK_VISIBILITY_LABELS } from '../../features/works/status'
import { CERTIFICATION_STATUS_LABELS } from '../../features/certifications/status'
import type { WorkCard as WorkCardData } from '../../types/work'

export interface WorkCardProps {
  work: WorkCardData
  to: string
}

export function WorkCard({ work, to }: WorkCardProps) {
  const certification = work.certification
  const isPublished = work.publication_status === 'published'
  const active = certification.status === 'submitted' || certification.status === 'under_review'
  const certificationTo = `${to}#certification`

  return (
    <article className="work-card">
      <Link className="work-card__link" to={to} aria-label={`Open work: ${work.title}`}>
        <MediaTile label={work.title} mediaId={work.cover_media_id} hideLabel />
        <div className="work-card__body">
          <div className="work-card__chips">
            <span className={`chip ${WORK_STATUS_CHIP[work.publication_status]}`}>
              {WORK_STATUS_LABELS[work.publication_status]}
            </span>
            <span className={`chip ${WORK_VISIBILITY_CHIP[work.visibility]}`}>
              {WORK_VISIBILITY_LABELS[work.visibility]}
            </span>
          </div>
          <h3 className="work-card__title">{work.title}</h3>
          <p className="work-card__summary">{work.summary}</p>
          {work.tags.length > 0 ? (
            <p className="work-card__tags" aria-label="Tags">
              {work.tags.slice(0, 4).map((tag) => (
                <span className="chip" key={tag}>
                  {tag}
                </span>
              ))}
            </p>
          ) : null}
        </div>
      </Link>

      <div className="work-card__action">
        {!isPublished ? (
          <p className="work-card__hint">Publish this work to apply for certification.</p>
        ) : certification.reviewable ? (
          <Link className="btn btn--ghost btn--sm" to={certificationTo}>
            {certification.status ? 'Request a New Review' : 'Apply for Certification'}
          </Link>
        ) : active && certification.status ? (
          <p className="work-card__cert">{CERTIFICATION_STATUS_LABELS[certification.status]}</p>
        ) : null}
      </div>
    </article>
  )
}
