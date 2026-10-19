/**
 * Projects page — the full public project index, filterable by project type
 * via the `?type=` query parameter. Featured member contributions (curated by
 * the lab) are merged in alongside hand-built projects.
 */

import { Link, useSearchParams } from 'react-router-dom'
import { PageHeader } from '../../components/public/PageHeader'
import { ProjectCard } from '../../components/public/ProjectCard'
import { ContributionCard } from '../../components/public/ContributionCard'
import { Reveal } from '../../components/public/Reveal'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { usePublicProjects } from '../../features/projects/hooks'
import { useFeaturedContributions } from '../../features/works/hooks'
import { absolutePageUrl, useDefaultOgImage, usePageMeta } from '../../lib/utils/seo'
import type { ProjectType } from '../../types/content'
import type { FeaturedContribution } from '../../types/work'
import type { PublicProject } from '../../types/content'

const FILTERS: Array<{ value: ProjectType | null; label: string }> = [
  { value: null, label: 'All' },
  { value: 'client-work', label: 'Client work' },
  { value: 'product', label: 'Products' },
  { value: 'experiment', label: 'Experiments' },
  { value: 'member-contribution', label: 'Member contributions' },
]

type Entry =
  | { kind: 'project'; key: string; type: ProjectType; project: PublicProject }
  | { kind: 'contribution'; key: string; type: ProjectType; contribution: FeaturedContribution }

function isProjectType(value: string | null): value is ProjectType {
  return (
    value === 'client-work' ||
    value === 'product' ||
    value === 'experiment' ||
    value === 'member-contribution'
  )
}

export default function ProjectsPage() {
  const [params] = useSearchParams()
  const rawType = params.get('type')
  const active = isProjectType(rawType) ? rawType : null
  const { data, loading, error, reload } = usePublicProjects({ sort: 'display_order', order: 'asc' })
  const { data: contributionsData } = useFeaturedContributions()

  const ogImage = useDefaultOgImage()
  usePageMeta({
    title: 'Projects — Thridha Labs',
    description:
      'Selected work and experiments from Thridha Labs — AI, software and ideas turned into things people can use.',
    canonical: absolutePageUrl('/projects'),
    ogImage,
  })

  const projects = data?.items ?? []
  const contributions = contributionsData?.items ?? []
  const entries: Entry[] = [
    ...projects.map((project): Entry => ({
      kind: 'project',
      key: `project-${project.slug}`,
      type: project.project_type,
      project,
    })),
    ...contributions.map((contribution): Entry => ({
      kind: 'contribution',
      key: `contribution-${contribution.author.member_id}-${contribution.slug}`,
      type: contribution.classification,
      contribution,
    })),
  ]

  const visible = active ? entries.filter((entry) => entry.type === active) : entries

  const countFor = (value: ProjectType | null) =>
    value === null ? entries.length : entries.filter((entry) => entry.type === value).length

  return (
    <>
      <PageHeader
        eyebrow="Projects / index"
        title="Selected work and experiments"
        lede="A running log of what the lab builds — shipped products, client work, member contributions and things we are turning over in the name of research."
        meta={
          <p className="eyebrow" style={{ marginBottom: 0 }}>
            {data ? `${entries.length.toString().padStart(2, '0')} entries on file` : 'Indexing…'}
          </p>
        }
      />

      <div className="shell" style={{ paddingBlock: 'var(--space-7)' }}>
        <div className="filter-row" role="group" aria-label="Filter projects by type">
          <span className="filter-row__label">Filter</span>
          {FILTERS.map((filter) => {
            const isActive = active === filter.value
            const isFirst = filter.value === null
            const to = isFirst ? '/projects' : `/projects?type=${filter.value}`
            return (
              <Link
                key={filter.label}
                to={to}
                role="button"
                aria-pressed={isActive}
                className="pill"
                onClick={(event) => {
                  if (isActive) event.preventDefault()
                }}
              >
                {filter.label}
                <span className="visually-hidden"> — </span>
                <span aria-hidden="true">{countFor(filter.value)}</span>
              </Link>
            )
          })}
        </div>

        {loading ? (
          <ContentSkeleton rows={6} />
        ) : error ? (
          <ErrorState title="Unable to load projects" error={error} onRetry={reload} />
        ) : entries.length === 0 ? (
          <EmptyState title="No projects yet" description="Projects will appear here when published." />
        ) : visible.length === 0 ? (
          <EmptyState
            title={`No ${
              active === 'experiment'
                ? 'experiments'
                : active === 'product'
                  ? 'products'
                  : active === 'member-contribution'
                    ? 'member contributions'
                    : 'projects'
            } in this category`}
            description="Nothing is running under this filter yet."
          />
        ) : (
          <div className="project-grid">
            {visible.map((entry) => (
              <Reveal key={entry.key} className="reveal--grid">
                {entry.kind === 'project' ? (
                  <ProjectCard project={entry.project} featured={entry.project.featured} />
                ) : (
                  <ContributionCard contribution={entry.contribution} />
                )}
              </Reveal>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
