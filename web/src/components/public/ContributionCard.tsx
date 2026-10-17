/**
 * ContributionCard — a featured member work shown on the official Projects
 * page. Links to the member's public work page and credits the author.
 */

import { Link } from 'react-router-dom'
import type { FeaturedContribution } from '../../types/work'
import { MediaTile } from './MediaTile'
import { TechChips } from './TechChips'
import { PROJECT_TYPE_SHORT } from './labels'

export interface ContributionCardProps {
  contribution: FeaturedContribution
}

export function ContributionCard({ contribution }: ContributionCardProps) {
  const { author } = contribution
  return (
    <Link
      className="project-card project-card--featured"
      to={`/members/${author.member_id}/works/${contribution.slug}`}
      aria-label={`View member contribution: ${contribution.title}`}
    >
      <MediaTile label={contribution.title} mediaId={contribution.cover_media_id} large hideLabel />
      <div className="project-card__body">
        <div className="project-card__meta">
          <span className="project-card__type">{PROJECT_TYPE_SHORT[contribution.classification]}</span>
          <span className="flag">Featured</span>
        </div>
        <h3>{contribution.title}</h3>
        <p className="project-card__desc">{contribution.summary}</p>
        <TechChips items={contribution.tags.slice(0, 4)} />
        <span className="project-card__more">
          By {author.display_name} <span className="arrow" aria-hidden="true">→</span>
        </span>
      </div>
    </Link>
  )
}
