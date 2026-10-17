/**
 * Activity detail page — full brief for a published (or cancelled, clearly
 * marked) activity. Self-registration happens in the member portal; this page
 * links members there when registration is open.
 */

import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { MediaTile } from '../../components/public/MediaTile'
import { downloadPublicActivityBrief } from '../../features/activities/api'
import {
  ACTIVITY_TYPE_LABELS,
  ACTIVITY_TYPE_SHORT,
  PRESENTATION_LABELS,
  formatSchedule,
} from '../../features/activities/labels'
import { usePublicActivity } from '../../features/activities/hooks'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { NotFoundState } from '../../components/ui/NotFoundState'
import { getErrorMessage, isApiError } from '../../lib/errors/ApiError'
import { absolutePageUrl, usePageMeta } from '../../lib/utils/seo'

export default function ActivityDetailPage() {
  const { slug } = useParams<{ slug: string }>()
  const { data, loading, error, reload } = usePublicActivity(slug)
  const [downloading, setDownloading] = useState(false)
  const [briefError, setBriefError] = useState<string | null>(null)

  usePageMeta({
    title: data ? `${data.title} — Thridha Labs` : 'Activity — Thridha Labs',
    description: data?.summary || null,
    canonical: absolutePageUrl(`/activities/${slug ?? ''}`),
  })

  if (loading) return <ContentSkeleton rows={6} />
  if (error) {
    if (isApiError(error) && error.status === 404) return <NotFoundState />
    return <ErrorState title="Unable to load activity" error={error} onRetry={reload} />
  }
  if (!data) return <NotFoundState />

  const schedule = formatSchedule(data.start_date, data.end_date)

  async function handleDownloadBrief(): Promise<void> {
    setDownloading(true)
    setBriefError(null)
    try {
      const file = await downloadPublicActivityBrief(data!.slug)
      const url = URL.createObjectURL(file.blob)
      window.open(url, '_blank', 'noopener')
      setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch (caught) {
      setBriefError(getErrorMessage(caught, 'Could not open the brief.'))
    } finally {
      setDownloading(false)
    }
  }

  return (
    <article>
      <div className="detail-hero">
        <div className="shell">
          <Link className="back-link" to="/activities">
            <span className="arrow" aria-hidden="true">←</span> Back to activities
          </Link>
          <p className="eyebrow page-hero__eyebrow">
            <span className="hud-dot" aria-hidden="true" /> {ACTIVITY_TYPE_SHORT[data.activity_type]} ·{' '}
            {PRESENTATION_LABELS[data.presentation_status]}
          </p>
          <h1 className="detail-title">{data.title}</h1>
          {data.summary ? <p className="detail-lede">{data.summary}</p> : null}

          {data.presentation_status === 'cancelled' ? (
            <p className="notice notice--cancelled" role="alert">
              This activity has been cancelled.
            </p>
          ) : null}

          <dl className="meta-list">
            <div>
              <dt>Type</dt>
              <dd>{ACTIVITY_TYPE_LABELS[data.activity_type]}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{PRESENTATION_LABELS[data.presentation_status]}</dd>
            </div>
            {schedule ? (
              <div>
                <dt>Schedule</dt>
                <dd>{schedule}</dd>
              </div>
            ) : null}
            {data.roles_offered.length > 0 ? (
              <div>
                <dt>Roles</dt>
                <dd>{data.roles_offered.join(', ')}</dd>
              </div>
            ) : null}
            {data.has_brief ? (
              <div>
                <dt>Brief</dt>
                <dd>
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    disabled={downloading}
                    onClick={() => void handleDownloadBrief()}
                  >
                    {downloading ? 'Opening…' : 'Open PDF brief'}
                  </button>
                </dd>
              </div>
            ) : null}
          </dl>
          {briefError ? (
            <p className="form-field__error" role="alert">
              {briefError}
            </p>
          ) : null}

          {data.registration_open ? (
            <div className="cta-row" style={{ marginTop: 'var(--space-6)' }}>
              <Link className="btn btn--primary" to="/member/activities">
                Join in the member portal
              </Link>
            </div>
          ) : null}
        </div>
      </div>

      {data.banner_media_id ? (
        <section className="section" aria-label={`${data.title} banner`}>
          <div className="shell">
            <div className="activity-banner">
              <MediaTile label={data.title} mediaId={data.banner_media_id} aspect="wide" large hideLabel natural />
            </div>
          </div>
        </section>
      ) : null}

      {data.description ? (
        <section className="section" aria-label="About this activity">
          <div className="shell">
            <p className="eyebrow">About</p>
            <div className="prose">
              {data.description.split(/\n{2,}/).map((para, index) => (
                <p key={index}>{para}</p>
              ))}
            </div>
          </div>
        </section>
      ) : null}
    </article>
  )
}
