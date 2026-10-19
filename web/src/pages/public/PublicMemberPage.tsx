/**
 * Public member profile — a member's public details and their published,
 * public-visible works. Only reachable when the member is active with a public
 * profile; otherwise the API 404s and we show the not-found state.
 */

import { Link, useParams } from 'react-router-dom'
import { usePublicMember } from '../../features/members/hooks'
import { MemberAvatar } from '../../components/member/MemberAvatar'
import { MediaTile } from '../../components/public/MediaTile'
import { TechChips } from '../../components/public/TechChips'
import { ShareActions } from '../../components/public/ShareActions'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { NotFoundState } from '../../components/ui/NotFoundState'
import { EmptyState } from '../../components/ui/EmptyState'
import { isApiError } from '../../lib/errors/ApiError'
import { absolutePageUrl, memberShareImagePath, shareUrl, usePageMeta } from '../../lib/utils/seo'
import { useJsonLd } from '../../lib/hooks/useJsonLd'

function formatMonth(value: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short' })
}

function formatDate(value: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function contributionPeriod(start: string | null, end: string | null): string {
  const from = formatMonth(start)
  const to = formatMonth(end)
  if (from && to && from !== to) return `${from} – ${to}`
  if (from) return from
  if (to) return to
  return ''
}

export default function PublicMemberPage() {
  const { memberId } = useParams<{ memberId: string }>()
  const { data, loading, error, reload } = usePublicMember(memberId)

  const canonicalUrl = absolutePageUrl(`/members/${memberId ?? ''}`)
  const shareHref = shareUrl(`/members/${memberId ?? ''}`)
  const displayName = data?.display_name ?? 'Member'
  const shareImage = memberId ? absolutePageUrl(memberShareImagePath(memberId)) : null

  usePageMeta({
    title: data ? `${data.display_name} — Thridha Labs` : 'Member — Thridha Labs',
    description: data?.bio ?? null,
    canonical: canonicalUrl,
    ogImage: shareImage ?? undefined,
    ogImageAlt: data ? `Portrait of ${data.display_name}` : null,
    ogType: 'profile',
  })
  useJsonLd(
    data
      ? [
          {
            '@context': 'https://schema.org',
            '@type': 'Person',
            name: data.display_name,
            ...(data.bio ? { description: data.bio } : {}),
            url: absolutePageUrl(`/members/${data.member_id}`) ?? undefined,
            ...(data.location ? { address: data.location } : {}),
            ...(data.skills.length > 0 ? { knowsAbout: data.skills } : {}),
            ...(data.github_url || data.linkedin_url || data.portfolio_url
              ? {
                  sameAs: [data.github_url, data.linkedin_url, data.portfolio_url].filter(
                    (url): url is string => Boolean(url),
                  ),
                }
              : {}),
          },
        ]
      : [],
  )

  if (loading) return <ContentSkeleton rows={6} />
  if (error) {
    if (isApiError(error) && error.status === 404) return <NotFoundState />
    return <ErrorState title="Unable to load member" error={error} onRetry={reload} />
  }
  if (!data) return <NotFoundState />

  const contributions = data.contributions ?? []
  const works = data.works ?? []

  return (
    <article>
      <div className="detail-hero">
        <div className="shell">
          <p className="eyebrow page-hero__eyebrow">
            <span className="hud-dot" aria-hidden="true" /> Member · <span className="mono">{data.member_id}</span>
          </p>
          <div className="public-member__head">
            <MemberAvatar name={data.display_name} mediaId={data.picture_media_id} size="xl" accent />
            <div>
              <h1 className="detail-title">{data.display_name}</h1>
              {data.bio ? <p className="detail-lede">{data.bio}</p> : null}
            </div>
          </div>

          <dl className="meta-list">
            {data.location ? (
              <div>
                <dt>Location</dt>
                <dd>{data.location}</dd>
              </div>
            ) : null}
            {data.github_url ? (
              <div>
                <dt>GitHub</dt>
                <dd>
                  <a href={data.github_url} target="_blank" rel="noreferrer">
                    Profile <span aria-hidden="true">↗</span>
                  </a>
                </dd>
              </div>
            ) : null}
            {data.linkedin_url ? (
              <div>
                <dt>LinkedIn</dt>
                <dd>
                  <a href={data.linkedin_url} target="_blank" rel="noreferrer">
                    Profile <span aria-hidden="true">↗</span>
                  </a>
                </dd>
              </div>
            ) : null}
            {data.portfolio_url ? (
              <div>
                <dt>Portfolio</dt>
                <dd>
                  <a href={data.portfolio_url} target="_blank" rel="noreferrer">
                    Website <span aria-hidden="true">↗</span>
                  </a>
                </dd>
              </div>
            ) : null}
          </dl>

          {data.skills.length > 0 ? (
            <div className="public-member__tags">
              <span className="eyebrow">Skills</span>
              <p className="tech-chips">
                {data.skills.map((skill) => (
                  <span className="chip" key={skill}>
                    {skill}
                  </span>
                ))}
              </p>
            </div>
          ) : null}
          {data.interests.length > 0 ? (
            <div className="public-member__tags">
              <span className="eyebrow">Interests</span>
              <p className="tech-chips">
                {data.interests.map((interest) => (
                  <span className="chip" key={interest}>
                    {interest}
                  </span>
                ))}
              </p>
            </div>
          ) : null}

          {data ? (
            <ShareActions
              url={shareHref}
              title={`${displayName} — Thridha Labs`}
              text={data.bio ?? undefined}
            />
          ) : null}
        </div>
      </div>

      {contributions.length > 0 ? (
        <section className="section" aria-label={`${data.display_name} verified contributions`}>
          <div className="shell">
            <p className="eyebrow">Verified contributions</p>
            <p className="section-lede">
              Approved project work, reviewed and summarized by the lab team.
            </p>
            <ul className="contribution-list">
              {contributions.map((contribution) => {
                const period = contributionPeriod(
                  contribution.period_start,
                  contribution.period_end,
                )
                return (
                  <li
                    key={`${contribution.activity_title}-${contribution.published_at}`}
                    className="contribution-card"
                  >
                    <div className="contribution-card__meta">
                      <span className="chip chip--ok">Verified contribution</span>
                      {contribution.role ? (
                        <span className="chip chip--muted">{contribution.role}</span>
                      ) : null}
                    </div>
                    <h3 className="contribution-card__title">{contribution.activity_title}</h3>
                    <p className="contribution-card__dates mono">
                      {period ? <>Contribution period {period}</> : null}
                      {period && contribution.published_at ? ' · ' : ''}
                      {contribution.published_at
                        ? `Published ${formatDate(contribution.published_at)}`
                        : ''}
                      {contribution.source_report_count > 0
                        ? ` · ${contribution.source_report_count} approved report${
                            contribution.source_report_count === 1 ? '' : 's'
                          }`
                        : ''}
                    </p>
                    <p className="contribution-card__desc">{contribution.content}</p>
                  </li>
                )
              })}
            </ul>
          </div>
        </section>
      ) : null}

      <section className="section" aria-label={`${data.display_name} works`}>
        <div className="shell">
          <p className="eyebrow">Selected work</p>
          {works.length === 0 ? (
            <EmptyState title="No public works yet" description="This member has not published any public work." />
          ) : (
            <ul className="public-work-grid">
              {works.map((work) => (
                <li key={work.slug}>
                  <Link
                    className="project-card"
                    to={`/members/${data.member_id}/works/${work.slug}`}
                    aria-label={`View work: ${work.title}`}
                  >
                    <MediaTile label={work.title} mediaId={work.cover_media_id} hideLabel />
                    <div className="project-card__body">
                      <h3>{work.title}</h3>
                      <p className="project-card__desc">{work.summary}</p>
                      {work.tags.length > 0 ? (
                        <div className="project-card__tags">
                          <TechChips items={work.tags} limit={4} />
                        </div>
                      ) : null}
                      <span className="project-card__more">
                        View work <span className="arrow" aria-hidden="true">→</span>
                      </span>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </article>
  )
}

