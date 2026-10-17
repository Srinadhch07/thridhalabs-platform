/**
 * Public certificate verification page.
 *
 * Resolves a certificate ID against `GET /api/public/certificates/{id}` and
 * reports only the public projection: status, issue date, member display name,
 * the certified work title and (when both the member and work are public) a
 * link to the work. Unknown or guessed IDs resolve to an "unverified" state
 * and never leak private work content.
 */

import { Link, useParams } from 'react-router-dom'
import { usePublicCertificate } from '../../features/certificates/hooks'
import { CertificateStatusChip } from '../../components/certificates/CertificateStatusChip'
import { CertifiedWorkSection } from '../../components/certificates/CertifiedWorkSection'
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

export default function VerifyCertificatePage() {
  const { certificateId } = useParams<{ certificateId: string }>()
  const { data, loading, error, reload } = usePublicCertificate(certificateId)

  usePageMeta({
    title: 'Verify a certificate — Thridha Labs',
    description:
      'Verify the authenticity and status of a Thridha Labs work certificate.',
    canonical: absolutePageUrl(`/verify-certificate/${certificateId ?? ''}`),
  })

  if (loading) return <ContentSkeleton rows={5} />

  if (error) {
    if (isApiError(error) && error.status === 404) {
      return (
        <section className="section">
          <div className="shell verify-page">
            <p className="eyebrow">
              <span className="hud-dot" aria-hidden="true" /> Certificate verification
            </p>
            <h1 className="detail-title">Certificate not found</h1>
            <p className="detail-lede">
              No certificate matches the ID{' '}
              <span className="mono">{certificateId ?? '—'}</span>. Check the ID and try again — it
              is printed on the certificate and encoded in its QR code.
            </p>
            <Link className="btn btn--ghost" to="/">
              Back to home
            </Link>
          </div>
        </section>
      )
    }
    return <ErrorState title="Unable to verify certificate" error={error} onRetry={reload} />
  }

  if (!data) return null

  const revoked = data.status === 'revoked'

  return (
    <section className="section">
      <div className="shell verify-page">
        <p className="eyebrow">
          <span className="hud-dot" aria-hidden="true" /> Certificate verification
        </p>

        <div className={`verify-card${revoked ? ' verify-card--revoked' : ''}`}>
          <div className="verify-card__head">
            <CertificateStatusChip status={data.status} />
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
              <dt>Certified work</dt>
              <dd>
                {data.work_url ? (
                  <a href={data.work_url}>{data.work_title} ↗</a>
                ) : (
                  data.work_title
                )}
              </dd>
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

          {revoked && data.revocation_reason ? (
            <p className="verify-card__reason" role="status">
              Reason: {data.revocation_reason}
            </p>
          ) : null}

          <p className="verify-card__note">
            This verifies that Thridha Labs reviewed and certified one specific submitted work. It
            is not a government, academic, or professional-accreditation credential.
          </p>
        </div>

        {data.work ? <CertifiedWorkSection work={data.work} /> : null}
      </div>
    </section>
  )
}
