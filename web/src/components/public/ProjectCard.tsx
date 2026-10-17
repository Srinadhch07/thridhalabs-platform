/**
 * ProjectCard — one entry in a project grid. The whole card is a link to the
 * project detail page; featured cards carry a stronger frame + flag.
 */

import { Link } from 'react-router-dom'
import type { PublicProject } from '../../types/content'
import { MediaTile } from './MediaTile'
import { TechChips } from './TechChips'
import { PROJECT_TYPE_SHORT } from './labels'

export interface ProjectCardProps {
  project: PublicProject
  featured?: boolean
}

export function ProjectCard({ project, featured = false }: ProjectCardProps) {
  return (
    <Link
      className={`project-card${featured ? ' project-card--featured' : ''}`}
      to={`/projects/${project.slug}`}
      aria-label={`View project: ${project.name}`}
    >
      <MediaTile label={project.name} mediaId={project.thumbnail_media_id} large={featured} hideLabel />
      <div className="project-card__body">
        <div className="project-card__meta">
          <span className="project-card__type">{PROJECT_TYPE_SHORT[project.project_type]}</span>
          {featured && <span className="flag">Featured</span>}
          {project.category && <span>· {project.category}</span>}
        </div>
        <h3>{project.name}</h3>
        <p className="project-card__desc">{project.description}</p>
        <TechChips items={project.technologies.slice(0, 4)} />
        <span className="project-card__more">
          View case file <span className="arrow" aria-hidden="true">→</span>
        </span>
      </div>
    </Link>
  )
}