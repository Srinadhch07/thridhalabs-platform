/** CertificatePanel — admin certificate issuance, delivery and revocation.
 *
 * Shown alongside a certification review. When the (approved) request has no
 * certificate yet, an admin/owner can "Approve & Generate Certificate". Once a
 * certificate exists, its identity, PDF, verification link, email delivery and
 * revocation controls are surfaced here.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  emailCertificate,
  issueCertificate,
  revokeCertificate,
} from '../../features/certificates/api'
import { useAdminCertificate } from '../../features/certificates/hooks'
import { CertificateSummary } from './CertificateSummary'
import { FormField } from '../form/FormField'
import { Textarea } from '../form/Textarea'
import { SaveButton } from '../form/SaveButton'
import { InlineLoader } from '../ui/InlineLoader'
import { ErrorState } from '../ui/ErrorState'
import { getErrorMessage } from '../../lib/errors/ApiError'
import type { CertificationStatus } from '../../types/certification'

function CertificateControls({
  certificateId,
  canManage,
  onChanged,
}: {
  certificateId: string
  canManage: boolean
  onChanged: () => void
}) {
  const { data, loading, error, reload } = useAdminCertificate(certificateId)
  const [busy, setBusy] = useState<'email' | 'revoke' | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [reason, setReason] = useState('')
  const [revoking, setRevoking] = useState(false)

  async function handleEmail(): Promise<void> {
    setActionError(null)
    setNotice(null)
    setBusy('email')
    try {
      await emailCertificate(certificateId)
      setNotice('Certificate emailed to the member.')
      reload()
    } catch (caught) {
      setActionError(getErrorMessage(caught, 'Could not email the certificate.'))
    } finally {
      setBusy(null)
    }
  }

  async function handleRevoke(): Promise<void> {
    if (!reason.trim()) {
      setActionError('A reason is required to revoke a certificate.')
      return
    }
    setActionError(null)
    setNotice(null)
    setBusy('revoke')
    try {
      await revokeCertificate(certificateId, { reason: reason.trim() })
      setNotice('Certificate revoked.')
      setRevoking(false)
      setReason('')
      reload()
      onChanged()
    } catch (caught) {
      setActionError(getErrorMessage(caught, 'Could not revoke the certificate.'))
    } finally {
      setBusy(null)
    }
  }

  if (loading) return <InlineLoader label="Loading certificate…" />
  if (error) return <ErrorState error={error} onRetry={reload} />
  if (!data) return null

  return (
    <div className="certificate-panel__issued">
      <CertificateSummary certificate={data} scope="admin" />

      <p className="certificate-panel__hint">
        <Link to={`/admin/certificates?request_id=${data.request_id}`}>Open in certificates queue</Link>
      </p>

      {data.email_last_error ? (
        <p className="certificate-panel__error" role="status">
          Last email attempt failed: {data.email_last_error}
        </p>
      ) : null}

      {canManage ? (
        <div className="certificate-panel__controls">
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => void handleEmail()}
            disabled={busy !== null}
          >
            {busy === 'email' ? 'Sending…' : data.email_status === 'sent' ? 'Resend email' : 'Email certificate'}
          </button>
          {data.status === 'issued' ? (
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => setRevoking((value) => !value)}
              disabled={busy !== null}
            >
              {revoking ? 'Cancel revoke' : 'Revoke'}
            </button>
          ) : null}
        </div>
      ) : (
        <p className="certificate-panel__hint">Only admins and owners can email or revoke certificates.</p>
      )}

      {revoking ? (
        <div className="certificate-panel__revoke">
          <FormField id="cert-revoke-reason" label="Revocation reason" hint="Required">
            <Textarea
              id="cert-revoke-reason"
              rows={3}
              value={reason}
              onChange={setReason}
              placeholder="Why is this certificate being revoked?"
            />
          </FormField>
          <SaveButton busy={busy === 'revoke'} disabled={busy !== null} onClick={() => void handleRevoke()}>
            Confirm revocation
          </SaveButton>
        </div>
      ) : null}

      {actionError ? (
        <p className="form-field__error form-field__error--form" role="alert">
          {actionError}
        </p>
      ) : null}
      {notice ? (
        <p className="admin-form__dirty" role="status">
          {notice}
        </p>
      ) : null}
    </div>
  )
}

export function CertificatePanel({
  requestId,
  requestStatus,
  certificateId,
  canManage,
  onChanged,
}: {
  requestId: string
  requestStatus: CertificationStatus
  certificateId: string | null
  canManage: boolean
  onChanged: () => void
}) {
  const [busy, setBusy] = useState(false)
  const [issueError, setIssueError] = useState<string | null>(null)

  async function handleIssue(): Promise<void> {
    setIssueError(null)
    setBusy(true)
    try {
      await issueCertificate({ request_id: requestId })
      onChanged()
    } catch (caught) {
      setIssueError(getErrorMessage(caught, 'Could not generate the certificate.'))
    } finally {
      setBusy(false)
    }
  }

  if (certificateId) {
    return (
      <div className="certificate-panel">
        <h2 className="cert-review__title">Certificate</h2>
        <CertificateControls
          certificateId={certificateId}
          canManage={canManage}
          onChanged={onChanged}
        />
      </div>
    )
  }

  const approvable = requestStatus === 'approved'
  const issuable = approvable || requestStatus === 'submitted' || requestStatus === 'under_review'

  return (
    <div className="certificate-panel">
      <h2 className="cert-review__title">Certificate</h2>
      {!canManage ? (
        <p className="cert-review__note">Only admins and owners can issue certificates.</p>
      ) : !issuable ? (
        <p className="cert-review__note">
          A certificate can be issued once this request is approved.
        </p>
      ) : (
        <>
          <p className="cert-review__note">
            {approvable
              ? 'This request is approved — generate its certificate.'
              : 'Generating the certificate will also approve this request.'}
          </p>
          <SaveButton busy={busy} onClick={() => void handleIssue()}>
            Approve &amp; Generate Certificate
          </SaveButton>
        </>
      )}
      {issueError ? (
        <p className="form-field__error form-field__error--form" role="alert">
          {issueError}
        </p>
      ) : null}
    </div>
  )
}
