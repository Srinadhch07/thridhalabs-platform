/**
 * Work preview — renders a work exactly as the public page would, using the
 * member's own (possibly unpublished) content. Media resolves through the
 * public delivery route so the preview matches production.
 */

import { Link, useParams } from 'react-router-dom'
import { useMemberWork } from '../../features/works/hooks'
import { useMemberSessionIssue } from '../../lib/hooks/useMemberSession'
import { usePageMeta } from '../../lib/utils/seo'
import { WORK_STATUS_CHIP, WORK_STATUS_LABELS, WORK_VISIBILITY_LABELS } from '../../features/works/status'
import { ContentRenderer } from '../../components/works/ContentRenderer'
import { MediaTile } from '../../components/public/MediaTile'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { NotFoundState } from '../../components/ui/NotFoundState'
import { isApiError } from '../../lib/errors/ApiError'

export default function WorkPreviewPage() {
  const { workId } = useParams<{ workId: string }>()
  const { data, loading, error, reload } = useMemberWork(workId)
  useMemberSessionIssue(error)

  usePageMeta({ title: data ? `Preview: ${data.title} — Member portal` : 'Work preview — Member portal' })

  if (loading) return <ContentSkeleton rows={6} />
  if (error) {
    if (isApiError(error) && error.status === 404) return <NotFoundState />
    return <ErrorState error={error} onRetry={reload} />
  }
  if (!data) return <NotFoundState />

  const isPubliclyVisible = data.publication_status === 'published' && data.visibility === 'public'

  return (
    <div className="member-page">
      <div className="work-preview__bar">
        <Link className="btn btn--ghost btn--sm" to={`/member/works/${data.id}/edit`}>
          Back to editor
        </Link>
        <div className="work-preview__chips">
          <span className={`chip ${WORK_STATUS_CHIP[data.publication_status]}`}>
            {WORK_STATUS_LABELS[data.publication_status]}
          </span>
          <span className="chip">{WORK_VISIBILITY_LABELS[data.visibility]}</span>
        </div>
      </div>

      {!isPubliclyVisible ? (
        <p className="work-preview__notice" role="status">
          This work is not publicly visible yet. It will appear on your public profile once it is
          published, set to public, and your profile is public.
        </p>
      ) : null}

      <article className="work-public">
        <header className="work-public__head">
          <h1 className="work-public__title">{data.title}</h1>
          <p className="work-public__summary">{data.summary}</p>
          {data.tags.length > 0 ? (
            <p className="tech-chips" aria-label="Tags">
              {data.tags.map((tag) => (
                <span className="chip" key={tag}>
                  {tag}
                </span>
              ))}
            </p>
          ) : null}
        </header>

        {data.cover_media_id ? (
          <div className="work-public__cover">
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
      </article>
    </div>
  )
}
