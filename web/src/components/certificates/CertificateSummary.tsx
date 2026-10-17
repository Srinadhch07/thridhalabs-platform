/** CertificateSummary — certificate identity + verified links + PDF download.
 *
 * Shared by the member portal and the admin review surfaces. The download goes
 * through a scope-specific authorized endpoint (members may only fetch their
 * own certificates; admins may fetch any).
 */

import { useState } from 'react'
import { downloadAdminCertificate, downloadMemberCertificate } from '../../features/certificates/api'
import {
  CERTIFICATE_EMAIL_CHIP,
  CERTIFICATE_EMAIL_LABELS,
} from '../../features/certificates/status'
import { CertificateStatusChip } from './CertificateStatusChip'
import { saveBlob } from '../../lib/utils/download'
import { getErrorMessage } from '../../lib/errors/ApiError'
import type { CertificateAdmin, CertificateMember } from '../../types/certificate'

function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
}

export function CertificateSummary({
  certificate,
  scope,
}: {
  certificate: CertificateMember | CertificateAdmin
  scope: 'admin' | 'member'
}) {
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  async function handleDownload(): Promise<void> {
    setDownloadError(null)
    setDownloading(true)
    try {
      const fetchPdf = scope === 'admin' ? downloadAdminCertificate : downloadMemberCertificate
      const { blob, filename } = await fetchPdf(certificate.certificate_id)
      saveBlob(blob, filename ?? certificate.pdf_filename)
    } catch (caught) {
      setDownloadError(getErrorMessage(caught, 'Could not download the certificate.'))
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="certificate-summary">
      <div className="certificate-summary__head">
        <CertificateStatusChip status={certificate.status} />
        <span className={`chip ${CERTIFICATE_EMAIL_CHIP[certificate.email_status]}`}>
          {CERTIFICATE_EMAIL_LABELS[certificate.email_status]}
        </span>
      </div>

      <dl className="cert-meta">
        <div>
          <dt>Certificate ID</dt>
          <dd className="mono">{certificate.certificate_id}</dd>
        </div>
        <div>
          <dt>Issued</dt>
          <dd>{formatDate(certificate.issued_at)}</dd>
        </div>
        {certificate.status === 'revoked' ? (
          <div>
            <dt>Revoked</dt>
            <dd>{formatDate(certificate.revoked_at)}</dd>
          </div>
        ) : null}
      </dl>

      {certificate.status === 'revoked' && certificate.revocation_reason ? (
        <p className="certificate-summary__revoked" role="status">
          Revoked: {certificate.revocation_reason}
        </p>
      ) : null}

      <div className="certificate-summary__actions">
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() => void handleDownload()}
          disabled={downloading}
        >
          {downloading ? 'Preparing…' : 'Download Certificate'}
        </button>
        <a
          className="btn btn--ghost btn--sm"
          href={certificate.verify_url}
          target="_blank"
          rel="noreferrer"
        >
          Verification page ↗
        </a>
      </div>
      {downloadError ? (
        <p className="form-field__error form-field__error--form" role="alert">
          {downloadError}
        </p>
      ) : null}
    </div>
  )
}
