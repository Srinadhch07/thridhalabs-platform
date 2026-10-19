/**
 * Public work page — a single published, public-visible work by member + slug.
 * Renders the member's structured content, tags, cover and external links.
 */

import { Link, useParams } from 'react-router-dom'
import { usePublicWork } from '../../features/works/hooks'
import { ContentRenderer } from '../../components/works/ContentRenderer'
import { MediaTile } from '../../components/public/MediaTile'
import { TechChips } from '../../components/public/TechChips'
import { ShareActions } from '../../components/public/ShareActions'
import { MemberAvatar } from '../../components/member/MemberAvatar'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { NotFoundState } from '../../components/ui/NotFoundState'
import { isApiError } from '../../lib/errors/ApiError'
import { absolutePageUrl, shareUrl, usePageMeta, workShareImagePath } from '../../lib/utils/seo'
import { useJsonLd } from '../../lib/hooks/useJsonLd'

function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
}

export default function PublicWorkPage() {
  const { memberId, slug } = useParams<{ memberId: string; slug: string }>()
  const { data, loading, error, reload } = usePublicWork(memberId, slug)

  const canonicalUrl = absolutePageUrl(`/members/${memberId ?? ''}/works/${slug ?? ''}`)
  const shareHref = shareUrl(`/members/${memberId ?? ''}/works/${slug ?? ''}`)
  const shareImage =
    memberId && slug ? absolutePageUrl(workShareImagePath(memberId, slug)) : null

  usePageMeta({
    title: data ? `${data.title} — Thridha Labs` : 'Work — Thridha Labs',
    description: data?.summary ?? null,
    canonical: canonicalUrl,
    ogImage: shareImage ?? undefined,
    ogImageAlt: data ? `Cover image for ${data.title}` : null,
    ogType: 'article',
  })
  useJsonLd(
    data
      ? [
          {
            '@context': 'https://schema.org',
            '@type': 'CreativeWork',
            name: data.title,
            description: data.summary,
            url: absolutePageUrl(`/members/${memberId}/works/${data.slug}`) ?? undefined,
            ...(shareImage ? { image: shareImage } : {}),
            ...(data.tags.length > 0 ? { keywords: data.tags.join(', ') } : {}),
            author: {
              '@type': 'Person',
              name: data.author.display_name,
              url: absolutePageUrl(`/members/${data.author.member_id}`) ?? undefined,
            },
            ...(data.published_at ? { datePublished: data.published_at } : {}),
          },
        ]
      : [],
  )

  if (loading) return <ContentSkeleton rows={6} />
  if (error) {
    if (isApiError(error) && error.status === 404) return <NotFoundState />
    return <ErrorState title="Unable to load work" error={error} onRetry={reload} />
  }
  if (!data) return <NotFoundState />

  return (
    <article className="work-public-page">
      <div className="detail-hero">
        <div className="shell">
          <Link className="back-link" to={`/members/${data.author.member_id}`}>
            <span className="arrow" aria-hidden="true">
              ←
            </span>{' '}
            {data.author.display_name}
          </Link>
          <p className="eyebrow page-hero__eyebrow">
            <span className="hud-dot" aria-hidden="true" /> Work
          </p>
          <h1 className="detail-title">{data.title}</h1>
          <p className="detail-lede">{data.summary}</p>

          <div className="work-public__byline">
            <MemberAvatar name={data.author.display_name} mediaId={data.author.picture_media_id} size="sm" />
            <span>
              {data.author.display_name}
              {data.published_at ? ` · ${formatDate(data.published_at)}` : ''}
            </span>
          </div>

          {data.tags.length > 0 ? <TechChips items={data.tags} /> : null}

          {data ? (
            <ShareActions
              url={shareHref}
              title={`${data.title} — Thridha Labs`}
              text={data.summary}
            />
          ) : null}
        </div>
      </div>

      <section className="section">
        <div className="shell">
          {data.cover_media_id ? (
            <div className="work-public__cover work-public__cover--page">
              <MediaTile label={data.title} mediaId={data.cover_media_id} large />
            </div>
          ) : null}
          <ContentRenderer document={data.content} />
          {data.external_links.length > 0 ? (
            <section className="work-public__links" aria-label="External links">
              <h2 className="work-heading">Links</h2>
              <ul className="work-public__link-list">
                {data.external_links.map((link) => (
                  <li key={link.url}>
                    <a href={link.url} target="_blank" rel="noreferrer">
                      {link.label} <span aria-hidden="true">↗</span>
                    </a>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      </section>
    </article>
  )
}
