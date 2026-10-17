/**
 * Member certifications — the member's certification requests with status,
 * reviewer feedback and an expandable detail (frozen snapshot + history).
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMemberCertifications, useMemberCertification } from '../../features/certifications/hooks'
import { useMemberSessionIssue } from '../../lib/hooks/useMemberSession'
import { usePageMeta } from '../../lib/utils/seo'
import { CERTIFICATION_STATUS_LABELS } from '../../features/certifications/status'
import { MemberPageHeader } from '../../components/member/MemberPageHeader'
import { MemberEmptyState } from '../../components/member/MemberEmptyState'
import { MemberCard } from '../../components/member/MemberCard'
import { CertificationStatusChip } from '../../components/certifications/CertificationStatusChip'
import { CertificationDetailPanel } from '../../components/certifications/CertificationDetailPanel'
import { Select } from '../../components/form/Select'
import { Pagination } from '../../components/admin/Pagination'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { InlineLoader } from '../../components/ui/InlineLoader'
import type { CertificationStatus } from '../../types/certification'

function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function MemberDetailPanel({ requestId }: { requestId: string }) {
  const { data, loading, error, reload } = useMemberCertification(requestId)
  useMemberSessionIssue(error)
  if (loading) return <InlineLoader label="Loading request…" />
  if (error) return <ErrorState error={error} onRetry={reload} />
  if (!data) return null
  return <CertificationDetailPanel detail={data} certificateScope="member" />
}

export default function MemberCertificationsPage() {
  usePageMeta({ title: 'Certifications — Member portal — Thridha Labs' })

  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<'' | CertificationStatus>('')
  const [expanded, setExpanded] = useState<string | null>(null)

  const { data, loading, error, reload } = useMemberCertifications({
    page,
    page_size: 10,
    status: status || undefined,
  })
  useMemberSessionIssue(error)

  const items = data?.items ?? []

  return (
    <div className="member-page">
      <MemberPageHeader
        title="Certification Requests"
        description="Apply for certification by submitting an eligible published work, then track its review here."
        actions={
          <Link className="btn btn--primary" to="/member/works">
            Start Certification Request
          </Link>
        }
      />

      {items.length > 0 ? (
        <p className="cert-page__helper" role="status">
          Apply for certification from your Work Showcase by choosing an eligible published work.
        </p>
      ) : null}

      <div className="member-toolbar">
        <Select
          id="certifications-status"
          aria-label="Filter by status"
          placeholder="All statuses"
          options={Object.entries(CERTIFICATION_STATUS_LABELS).map(([value, label]) => ({ value, label }))}
          value={status}
          onChange={(value) => {
            setStatus(value as '' | CertificationStatus)
            setPage(1)
          }}
        />
      </div>

      {loading ? <ContentSkeleton rows={4} /> : null}
      {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}

      {!loading && !error && items.length === 0 ? (
        <MemberEmptyState
          title={status ? 'No requests match that filter' : 'No certification requests yet'}
          description={
            status
              ? 'Try a different status.'
              : 'Choose an eligible published work from your Work Showcase and submit it for certification review.'
          }
          action={
            <Link className="btn btn--primary" to="/member/works">
              Start Certification Request
            </Link>
          }
        />
      ) : null}

      {items.length > 0 ? (
        <ul className="cert-list">
          {items.map((request) => (
            <li key={request.id}>
              <MemberCard>
                <div className="cert-list__head">
                  <div>
                    <h2 className="cert-list__title">{request.work.title}</h2>
                    <p className="cert-list__meta">
                      Submitted {formatDate(request.submitted_at)} · Snapshot v{request.snapshot_version}
                    </p>
                  </div>
                  <CertificationStatusChip status={request.status} />
                </div>
                {request.changed_since_review ? (
                  <p className="cert-list__warn" role="status">
                    This work changed after the review was decided.
                  </p>
                ) : null}
                <div className="cert-list__actions">
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    aria-expanded={expanded === request.id}
                    onClick={() => setExpanded(expanded === request.id ? null : request.id)}
                  >
                    {expanded === request.id ? 'Hide details' : 'View details'}
                  </button>
                  <Link className="btn btn--ghost btn--sm" to={`/member/works/${request.work.id}/edit`}>
                    Open work
                  </Link>
                </div>
                {expanded === request.id ? <MemberDetailPanel requestId={request.id} /> : null}
              </MemberCard>
            </li>
          ))}
        </ul>
      ) : null}

      {items.length > 0 ? (
        <Pagination page={data?.page ?? 1} pages={data?.pages ?? 1} total={data?.total ?? 0} onChange={setPage} />
      ) : null}
    </div>
  )
}
