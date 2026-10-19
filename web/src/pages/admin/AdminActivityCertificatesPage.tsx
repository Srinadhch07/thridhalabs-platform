/**
 * Admin activity certificates.
 *
 * Two sections: (1) an issue panel — pick an activity, load its confirmed
 * participants (eligibility is validated server-side), choose an award and issue
 * to one or many with per-recipient results; (2) the issued certificates list
 * with status/delivery filters and download/email/revoke actions.
 */

import { useState } from 'react'
import { useAdminActivities } from '../../features/activities/hooks'
import {
  bulkIssueActivityCertificates,
  downloadAdminActivityCertificate,
  emailActivityCertificate,
  issueActivityCertificate,
  revokeActivityCertificate,
} from '../../features/activityCertificates/api'
import {
  useAdminActivityCertificates,
  useEligibleParticipants,
} from '../../features/activityCertificates/hooks'
import {
  ACTIVITY_AWARD_LABELS,
  ACTIVITY_CERTIFICATE_EMAIL_CHIP,
  ACTIVITY_CERTIFICATE_EMAIL_LABELS,
  ACTIVITY_CERTIFICATE_STATUS_CHIP,
  ACTIVITY_CERTIFICATE_STATUS_LABELS,
} from '../../features/activityCertificates/status'
import { PageHeader } from '../../components/admin/PageHeader'
import { Pagination } from '../../components/admin/Pagination'
import { Select } from '../../components/form/Select'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { EmptyState } from '../../components/ui/EmptyState'
import { saveBlob } from '../../lib/utils/download'
import { getErrorMessage } from '../../lib/errors/ApiError'
import type { AdminActivity } from '../../types/activity'
import type {
  ActivityAwardCategory,
  ActivityCertificateAdmin,
  ActivityCertificateEligibleParticipant,
} from '../../types/activityCertificate'

function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString()
}

function alreadyIssuedFor(
  participant: ActivityCertificateEligibleParticipant,
  category: ActivityAwardCategory,
): boolean {
  if (category === 'custom') {
    return participant.already_issued_awards.some((key) => key.startsWith('custom:'))
  }
  return participant.already_issued_awards.includes(category)
}

// ---------------------------------------------------------------------------
// Issue panel
// ---------------------------------------------------------------------------
function IssuePanel({
  activities,
  onIssued,
}: {
  activities: AdminActivity[]
  onIssued: () => void
}) {
  const [activityId, setActivityId] = useState('')
  const [awardCategory, setAwardCategory] = useState<ActivityAwardCategory>('participation')
  const [customLabel, setCustomLabel] = useState('')
  const [customStatement, setCustomStatement] = useState('')
  const [selected, setSelected] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<string | null>(null)

  const { data, loading, error: loadError, reload } = useEligibleParticipants(
    activityId || undefined,
  )
  const participants = data?.items ?? []

  function payloadExtras() {
    if (awardCategory === 'custom') {
      return {
        custom_award_label: customLabel.trim() || null,
        custom_statement: customStatement.trim() || null,
      }
    }
    return {}
  }

  function toggle(memberId: string): void {
    setSelected((current) =>
      current.includes(memberId)
        ? current.filter((id) => id !== memberId)
        : [...current, memberId],
    )
  }

  async function handleIssueSelected(): Promise<void> {
    setError(null)
    setResult(null)
    if (!activityId) {
      setError('Choose an activity first.')
      return
    }
    if (selected.length === 0) {
      setError('Select at least one participant.')
      return
    }
    setBusy(true)
    try {
      const bulk = await bulkIssueActivityCertificates({
        activity_id: activityId,
        award_category: awardCategory,
        recipients: selected.map((memberId) => ({ member_id: memberId })),
      })
      setResult(
        `Issued ${bulk.issued_count} · skipped ${bulk.skipped_count} · failed ${bulk.failed_count}`,
      )
      setSelected([])
      reload()
      onIssued()
    } catch (caught) {
      setError(getErrorMessage(caught, 'Issuing failed.'))
    } finally {
      setBusy(false)
    }
  }

  async function handleIssueOne(memberId: string): Promise<void> {
    setError(null)
    setResult(null)
    setBusy(true)
    try {
      await issueActivityCertificate({
        activity_id: activityId,
        member_id: memberId,
        award_category: awardCategory,
        ...payloadExtras(),
      })
      setResult('Certificate issued.')
      reload()
      onIssued()
    } catch (caught) {
      setError(getErrorMessage(caught, 'Issuing failed.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="admin-panel">
      <h2 className="admin-panel__title">Issue activity certificates</h2>

      <div className="admin-toolbar">
        <Select
          id="activity-certificates-activity"
          aria-label="Activity"
          placeholder="Select an activity…"
          options={activities.map((activity) => ({
            value: activity.id,
            label: `${activity.title} (${activity.activity_type})`,
          }))}
          value={activityId}
          onChange={(value) => {
            setActivityId(value)
            setSelected([])
            setResult(null)
            setError(null)
          }}
        />
        <Select
          id="activity-certificates-award"
          aria-label="Award"
          options={Object.entries(ACTIVITY_AWARD_LABELS).map(([value, label]) => ({
            value,
            label,
          }))}
          value={awardCategory}
          onChange={(value) => setAwardCategory(value as ActivityAwardCategory)}
        />
        {awardCategory === 'custom' ? (
          <>
            <input
              className="input"
              aria-label="Custom award label"
              placeholder="Custom award label"
              value={customLabel}
              onChange={(event) => setCustomLabel(event.target.value)}
            />
            <input
              className="input"
              aria-label="Custom award statement"
              placeholder="Custom award statement (optional)"
              value={customStatement}
              onChange={(event) => setCustomStatement(event.target.value)}
            />
          </>
        ) : null}
      </div>

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      {result ? (
        <p className="form-note" role="status">
          {result}
        </p>
      ) : null}

      {!activityId ? (
        <p className="admin-panel__hint">
          Select an activity to list its confirmed participants.
        </p>
      ) : null}

      {activityId && loading ? <ContentSkeleton rows={3} /> : null}
      {activityId && loadError ? <ErrorState error={loadError} /> : null}

      {activityId && !loading && !loadError && participants.length === 0 ? (
        <EmptyState
          title="No confirmed participants"
          description="Only confirmed participants of this activity can be issued a certificate."
        />
      ) : null}

      {participants.length > 0 ? (
        <>
          <button
            type="button"
            className="btn btn--primary btn--sm"
            disabled={busy || selected.length === 0}
            onClick={() => void handleIssueSelected()}
          >
            Issue selected ({selected.length})
          </button>

          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th aria-label="Select" />
                  <th>Member</th>
                  <th>Status</th>
                  <th>Already issued</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {participants.map((participant) => (
                  <tr key={participant.member_id}>
                    <td>
                      <input
                        type="checkbox"
                        aria-label={`Select ${participant.member_name}`}
                        checked={selected.includes(participant.member_id)}
                        onChange={() => toggle(participant.member_id)}
                      />
                    </td>
                    <td>
                      {participant.member_name}
                      <span className="mono admin-table__sub">
                        {participant.member_readable_id}
                      </span>
                    </td>
                    <td>{participant.participation_status}</td>
                    <td>
                      {alreadyIssuedFor(participant, awardCategory) ? (
                        <span className="chip chip--muted">Issued</span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td>
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        disabled={busy}
                        onClick={() => void handleIssueOne(participant.member_id)}
                      >
                        Issue
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </section>
  )
}

// ---------------------------------------------------------------------------
// Issued-certificate row
// ---------------------------------------------------------------------------
function CertificateRow({
  certificate,
  onChanged,
}: {
  certificate: ActivityCertificateAdmin
  onChanged: () => void
}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [revoking, setRevoking] = useState(false)
  const [reason, setReason] = useState('')

  async function run(action: () => Promise<void>): Promise<void> {
    setError(null)
    setBusy(true)
    try {
      await action()
    } catch (caught) {
      setError(getErrorMessage(caught, 'Action failed.'))
    } finally {
      setBusy(false)
    }
  }

  async function handleRevoke(): Promise<void> {
    const trimmed = reason.trim()
    if (!trimmed) {
      setError('A revocation reason is required.')
      return
    }
    await run(async () => {
      await revokeActivityCertificate(certificate.certificate_id, { reason: trimmed })
      setRevoking(false)
      setReason('')
      onChanged()
    })
  }

  return (
    <tr>
      <td className="mono">{certificate.certificate_id}</td>
      <td>{certificate.activity_title}</td>
      <td>{certificate.award_label}</td>
      <td>{certificate.member_name}</td>
      <td>
        <span className={`chip ${ACTIVITY_CERTIFICATE_STATUS_CHIP[certificate.status]}`}>
          {ACTIVITY_CERTIFICATE_STATUS_LABELS[certificate.status]}
        </span>
      </td>
      <td>
        <span className={`chip ${ACTIVITY_CERTIFICATE_EMAIL_CHIP[certificate.email_status]}`}>
          {ACTIVITY_CERTIFICATE_EMAIL_LABELS[certificate.email_status]}
        </span>
      </td>
      <td>{formatDate(certificate.issued_at)}</td>
      <td>
        <div className="admin-table__actions">
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            disabled={busy}
            onClick={() =>
              void (async () => {
                setError(null)
                setBusy(true)
                try {
                  const { blob, filename } = await downloadAdminActivityCertificate(
                    certificate.certificate_id,
                  )
                  saveBlob(blob, filename ?? certificate.pdf_filename)
                } catch (caught) {
                  setError(getErrorMessage(caught, 'Download failed.'))
                } finally {
                  setBusy(false)
                }
              })()
            }
          >
            Download
          </button>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            disabled={busy}
            onClick={() =>
              void (async () => {
                setError(null)
                setBusy(true)
                try {
                  await emailActivityCertificate(certificate.certificate_id)
                  onChanged()
                } catch (caught) {
                  setError(getErrorMessage(caught, 'Email failed.'))
                } finally {
                  setBusy(false)
                }
              })()
            }
          >
            Email
          </button>
          {certificate.status === 'issued' ? (
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              disabled={busy}
              onClick={() => setRevoking((value) => !value)}
            >
              Revoke
            </button>
          ) : null}
          {revoking ? (
            <span className="admin-table__revoke">
              <input
                className="input input--sm"
                aria-label="Revocation reason"
                placeholder="Reason"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
              <button
                type="button"
                className="btn btn--danger btn--sm"
                disabled={busy}
                onClick={() => void handleRevoke()}
              >
                Confirm
              </button>
            </span>
          ) : null}
        </div>
        {error ? (
          <p className="form-error" role="alert">
            {error}
          </p>
        ) : null}
      </td>
    </tr>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function AdminActivityCertificatesPage() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<'' | keyof typeof ACTIVITY_CERTIFICATE_STATUS_LABELS>('')

  const { data: activityData } = useAdminActivities({ page_size: 100 })
  const activities = activityData?.items ?? []

  const { data, loading, error, reload } = useAdminActivityCertificates({
    page,
    page_size: 20,
    status: status || undefined,
  })

  return (
    <div>
      <PageHeader
        eyebrow="Review"
        title="Activity certificates"
        description="Participation and award certificates for programmes, hackathons and projects."
      />

      <IssuePanel activities={activities} onIssued={reload} />

      <section className="admin-panel">
        <h2 className="admin-panel__title">Issued certificates</h2>

        <div className="admin-toolbar">
          <Select
            id="activity-certificates-status"
            aria-label="Filter by status"
            placeholder="All statuses"
            options={Object.entries(ACTIVITY_CERTIFICATE_STATUS_LABELS).map(([value, label]) => ({
              value,
              label,
            }))}
            value={status}
            onChange={(value) => {
              setStatus(value as '' | keyof typeof ACTIVITY_CERTIFICATE_STATUS_LABELS)
              setPage(1)
            }}
          />
        </div>

        {loading ? <ContentSkeleton rows={5} /> : null}
        {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}

        {!loading && !error && (data?.items.length ?? 0) === 0 ? (
          <EmptyState
            title="No activity certificates"
            description="Issued certificates appear here."
          />
        ) : null}

        {data && data.items.length > 0 ? (
          <>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Certificate ID</th>
                    <th>Activity</th>
                    <th>Award</th>
                    <th>Member</th>
                    <th>Status</th>
                    <th>Email</th>
                    <th>Issued</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((certificate) => (
                    <CertificateRow
                      key={certificate.certificate_id}
                      certificate={certificate}
                      onChanged={reload}
                    />
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={data.page}
              pages={data.pages}
              total={data.total}
              onChange={setPage}
            />
          </>
        ) : null}
      </section>
    </div>
  )
}
