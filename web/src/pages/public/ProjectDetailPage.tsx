/**
 * Project detail page — single project case file: type metadata, description,
 * technologies, external links and a media gallery served through the public
 * media delivery endpoint.
 */

import { Link, useParams } from 'react-router-dom'
import { MediaTile } from '../../components/public/MediaTile'
import { TechChips } from '../../components/public/TechChips'
import { ShareActions } from '../../components/public/ShareActions'
import { PROJECT_TYPE_LABELS, PROJECT_TYPE_SHORT } from '../../components/public/labels'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { NotFoundState } from '../../components/ui/NotFoundState'
import { usePublicProject } from '../../features/projects/hooks'
import { isApiError } from '../../lib/errors/ApiError'
import { absolutePageUrl, projectShareImagePath, useBrandingOgImage, usePageMeta } from '../../lib/utils/seo'
import { useJsonLd } from '../../lib/hooks/useJsonLd'
import { resolveMediaUrl } from '../../lib/utils/mediaUrl'

export default function ProjectDetailPage() {
  const { slug } = useParams<{ slug: string }>()
  const { data, loading, error, reload } = usePublicProject(slug)

  const brandingOgImage = useBrandingOgImage()
  const canonicalUrl = absolutePageUrl(`/projects/${slug ?? ''}`)
  const shareImage = slug ? absolutePageUrl(projectShareImagePath(slug)) : null
  const contentImage = data?.thumbnail_media_id
    ? resolveMediaUrl(data.thumbnail_media_id, 'md')
    : (shareImage ?? brandingOgImage)
  const ogImage = shareImage ?? contentImage

  usePageMeta({
    title: data ? `${data.name} — Thridha Labs` : 'Project — Thridha Labs',
    description: data?.description || null,
    canonical: canonicalUrl,
    ogImage: ogImage,
    ogImageAlt: data ? `Preview of the ${data.name} project` : null,
  })
  useJsonLd(
    data
      ? [
          {
            '@context': 'https://schema.org',
            '@type': 'CreativeWork',
            name: data.name,
            description: data.description,
            url: absolutePageUrl(`/projects/${data.slug}`) ?? undefined,
            ...(contentImage ? { image: contentImage } : {}),
            ...(data.client?.name ? { creator: { '@type': 'Organization', name: data.client.name } } : {}),
            ...(data.technologies.length > 0 ? { keywords: data.technologies.join(', ') } : {}),
          },
        ]
      : [],
  )

  if (loading) return <ContentSkeleton rows={6} />
  if (error) {
    if (isApiError(error) && error.status === 404) return <NotFoundState />
    return <ErrorState title="Unable to load project" error={error} onRetry={reload} />
  }
  if (!data) return <NotFoundState />

  const gallery: Array<{ label: string; mediaId: string | null }> = []
  if (data.thumbnail_media_id) gallery.push({ label: data.name, mediaId: data.thumbnail_media_id })
  data.gallery_media_ids.forEach((id, index) => {
    gallery.push({ label: `${data.name} — frame ${index + 1}`, mediaId: id })
  })

  return (
    <article>
      <div className="detail-hero">
        <div className="shell">
          <Link className="back-link" to="/projects">
            <span className="arrow" aria-hidden="true">
              ←
            </span>{' '}
            Back to projects
          </Link>
          <p className="eyebrow page-hero__eyebrow">
            <span className="hud-dot" aria-hidden="true" /> Project · {PROJECT_TYPE_SHORT[data.project_type]}
          </p>
          <h1 className="detail-title">{data.name}</h1>
          <p className="detail-lede">{data.description}</p>

          <dl className="meta-list">
            <div>
              <dt>Type</dt>
              <dd>{PROJECT_TYPE_LABELS[data.project_type]}</dd>
            </div>
            {data.category && (
              <div>
                <dt>Category</dt>
                <dd>{data.category}</dd>
              </div>
            )}
            {data.client && (
              <div>
                <dt>Client</dt>
                <dd>
                  <Link to="/clients">{data.client.name}</Link>
                </dd>
              </div>
            )}
            {data.completion_date && (
              <div>
                <dt>Completed</dt>
                <dd>{data.completion_date}</dd>
              </div>
            )}
            {data.technologies.length > 0 && (
              <div>
                <dt>Stack</dt>
                <dd>
                  <TechChips items={data.technologies} />
                </dd>
              </div>
            )}
            {(data.live_url || data.github_url) && (
              <div>
                <dt>Links</dt>
                <dd>
                  {data.live_url && (
                    <a href={data.live_url} target="_blank" rel="noreferrer">
                      Live site <span aria-hidden="true">↗</span>
                    </a>
                  )}
                  {data.github_url && (
                    <>
                      {data.live_url && <span aria-hidden="true"> · </span>}
                      <a href={data.github_url} target="_blank" rel="noreferrer">
                        Source <span aria-hidden="true">↗</span>
                      </a>
                    </>
                  )}
                </dd>
              </div>
            )}
          </dl>

          {canonicalUrl ? (
            <ShareActions
              url={canonicalUrl}
              title={`${data.name} — Thridha Labs`}
              text={data.description || undefined}
            />
          ) : null}
        </div>
      </div>

      {gallery.length > 0 && (
        <section className="section" aria-label={`${data.name} catalogue`}>
          <div className="shell">
            <p className="eyebrow">Catalogue</p>
            <div className={gallery.length === 1 ? 'gallery-row' : 'gallery-row gallery-row--wide'}>
              {gallery.map((frame) => (
                <MediaTile
                  key={frame.label}
                  label={frame.label}
                  mediaId={frame.mediaId}
                  aspect="wide"
                />
              ))}
            </div>
          </div>
        </section>
      )}
    </article>
  )
}