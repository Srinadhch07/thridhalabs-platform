/**
 * Admin certificates — every issued certificate with status, delivery state and
 * a download action. Supports filtering by status and by originating request.
 */

import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { downloadAdminCertificate } from '../../features/certificates/api'
import { useAdminCertificates } from '../../features/certificates/hooks'
import {
  CERTIFICATE_EMAIL_CHIP,
  CERTIFICATE_EMAIL_LABELS,
  CERTIFICATE_STATUS_LABELS,
} from '../../features/certificates/status'
import { CertificateStatusChip } from '../../components/certificates/CertificateStatusChip'
import { PageHeader } from '../../components/admin/PageHeader'
import { Pagination } from '../../components/admin/Pagination'
import { Select } from '../../components/form/Select'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { EmptyState } from '../../components/ui/EmptyState'
import { saveBlob } from '../../lib/utils/download'
import { getErrorMessage } from '../../lib/errors/ApiError'
import type { CertificateAdmin, CertificateStatus } from '../../types/certificate'

function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString()
}

function CertificateRow({ certificate }: { certificate: CertificateAdmin }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleDownload(): Promise<void> {
    setError(null)
    setBusy(true)
    try {
      const { blob, filename } = await downloadAdminCertificate(certificate.certificate_id)
      saveBlob(blob, filename ?? certificate.pdf_filename)
    } catch (caught) {
      setError(getErrorMessage(caught, 'Download failed.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <tr>
      <td className="mono">{certificate.certificate_id}</td>
      <td>{certificate.work_title}</td>
      <td>
        {certificate.member_name}
      </td>
      <td>
        <CertificateStatusChip status={certificate.status} />
      </td>
      <td>
        <span className={`chip ${CERTIFICATE_EMAIL_CHIP[certificate.email_status]}`}>
          {CERTIFICATE_EMAIL_LABELS[certificate.email_status]}
        </span>
      </td>
      <td>{formatDate(certificate.issued_at)}</td>
      <td className="admin-table__actions">
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() => void handleDownload()}
          disabled={busy}
        >
          {busy ? 'Preparing…' : 'Download'}
        </button>
        <Link className="btn btn--ghost btn--sm" to={`/admin/certifications/${certificate.request_id}`}>
          Request
        </Link>
        {error ? (
          <span className="admin-table__sub" role="alert">
            {error}
          </span>
        ) : null}
      </td>
    </tr>
  )
}

export default function AdminCertificatesPage() {
  const [searchParams] = useSearchParams()
  const requestIdFilter = searchParams.get('request_id') ?? undefined

  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<'' | CertificateStatus>('')

  const { data, loading, error, reload } = useAdminCertificates({
    page,
    page_size: 20,
    status: status || undefined,
    request_id: requestIdFilter,
  })

  const items = data?.items ?? []

  return (
    <div>
      <PageHeader
        eyebrow="Review"
        title="Certificates"
        description="Certificates issued for approved certification requests."
      />

      <div className="admin-toolbar">
        <Select
          id="certificates-status"
          aria-label="Filter by status"
          placeholder="All statuses"
          options={Object.entries(CERTIFICATE_STATUS_LABELS).map(([value, label]) => ({
            value,
            label,
          }))}
          value={status}
          onChange={(value) => {
            setStatus(value as '' | CertificateStatus)
            setPage(1)
          }}
        />
      </div>

      {loading ? <ContentSkeleton rows={5} /> : null}
      {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}

      {!loading && !error && items.length === 0 ? (
        <EmptyState
          title="No certificates"
          description="Certificates appear here once an approved request is issued."
        />
      ) : null}

      {items.length > 0 ? (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Certificate ID</th>
                <th>Work</th>
                <th>Member</th>
                <th>Status</th>
                <th>Email</th>
                <th>Issued</th>
                <th className="admin-table__actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((certificate) => (
                <CertificateRow key={certificate.certificate_id} certificate={certificate} />
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {items.length > 0 ? (
        <Pagination
          page={data?.page ?? 1}
          pages={data?.pages ?? 1}
          total={data?.total ?? 0}
          onChange={setPage}
        />
      ) : null}
    </div>
  )
}
