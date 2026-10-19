/**
 * Public activity-certificate verification page.
 *
 * Resolves an activity certificate ID against
 * `GET /api/public/activity-certificates/{id}` and reports only the public
 * projection: status, issue date, member display name, the activity, the award
 * and (when both the member and work are public) a link to the recognized work.
 * Unknown or guessed IDs resolve to an "unverified" state and never leak
 * private data.
 */

import { Link, useParams } from 'react-router-dom'
import { usePublicActivityCertificate } from '../../features/activityCertificates/hooks'
import {
  ACTIVITY_CERTIFICATE_STATUS_CHIP,
  ACTIVITY_CERTIFICATE_STATUS_LABELS,
} from '../../features/activityCertificates/status'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { isApiError } from '../../lib/errors/ApiError'
import { absolutePageUrl, usePageMeta } from '../../lib/utils/seo'

function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
}

export default function VerifyActivityCertificatePage() {
  const { certificateId } = useParams<{ certificateId: string }>()
  const { data, loading, error, reload } = usePublicActivityCertificate(certificateId)

  usePageMeta({
    title: 'Verify an activity certificate — Thridha Labs',
    description:
      'Verify the authenticity and status of a Thridha Labs activity certificate.',
    canonical: absolutePageUrl(`/verify-activity-certificate/${certificateId ?? ''}`),
  })

  if (loading) return <ContentSkeleton rows={5} />

  if (error) {
    if (isApiError(error) && error.status === 404) {
      return (
        <section className="section">
          <div className="shell verify-page">
            <p className="eyebrow">
              <span className="hud-dot" aria-hidden="true" /> Activity certificate verification
            </p>
            <h1 className="detail-title">Certificate not found</h1>
            <p className="detail-body">
              We could not find an activity certificate with the ID{' '}
              <span className="mono">{certificateId}</span>. Check the ID printed on the
              certificate or encoded in its QR code.
            </p>
            <Link className="btn btn--ghost" to="/">
              Back to home
            </Link>
          </div>
        </section>
      )
    }
    return <ErrorState error={error} onRetry={reload} />
  }

  if (!data) return null

  const revoked = data.status === 'revoked'

  return (
    <section className="section">
      <div className="shell verify-page">
        <p className="eyebrow">
          <span className="hud-dot" aria-hidden="true" /> Activity certificate verification
        </p>

        <div className={`verify-card${revoked ? ' verify-card--revoked' : ''}`}>
          <div className="verify-card__head">
            <span className={`chip ${ACTIVITY_CERTIFICATE_STATUS_CHIP[data.status]}`}>
              {ACTIVITY_CERTIFICATE_STATUS_LABELS[data.status]}
            </span>
            <span className="mono verify-card__id">{data.certificate_id}</span>
          </div>

          <h1 className="verify-card__verdict">
            {revoked ? 'This certificate has been revoked' : 'Certificate verified'}
          </h1>

          <dl className="cert-meta">
            <div>
              <dt>Issued to</dt>
              <dd>{data.member_name}</dd>
            </div>
            <div>
              <dt>Activity</dt>
              <dd>
                {data.activity_title}
                <span className="muted"> · {data.activity_type}</span>
              </dd>
            </div>
            <div>
              <dt>Award</dt>
              <dd>{data.award_label}</dd>
            </div>
            <div>
              <dt>Issued</dt>
              <dd>{formatDate(data.issued_at)}</dd>
            </div>
            {revoked ? (
              <div>
                <dt>Revoked</dt>
                <dd>{formatDate(data.revoked_at)}</dd>
              </div>
            ) : null}
          </dl>

          {data.award_statement ? (
            <p className="verify-card__statement">{data.award_statement}</p>
          ) : null}

          {revoked && data.revocation_reason ? (
            <p className="verify-card__reason" role="status">
              Reason: {data.revocation_reason}
            </p>
          ) : null}

          {data.work ? (
            <p className="verify-card__work">
              Recognized work:{' '}
              <a href={data.work.url}>{data.work.title} ↗</a>
            </p>
          ) : null}

          <p className="verify-card__note">
            This verifies that Thridha Labs issued this activity certificate for participation
            or an award. It reflects participation in a Thridha Labs activity only and is not a
            government, academic or professional-accreditation credential.
          </p>
        </div>
      </div>
    </section>
  )
}
