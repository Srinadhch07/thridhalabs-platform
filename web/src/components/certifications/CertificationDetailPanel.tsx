/** CertificationDetailPanel — shared detail view for member and admin surfaces. */

import { CertificationStatusChip } from './CertificationStatusChip'
import { CertificationSnapshotView } from './CertificationSnapshotView'
import { DecisionHistory } from './DecisionHistory'
import { CertificateRefSection } from '../certificates/CertificateRefSection'
import type { CertificationDetail } from '../../types/certification'

function formatDateTime(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function CertificationDetailPanel({
  detail,
  showMember = false,
  certificateScope,
}: {
  detail: CertificationDetail
  showMember?: boolean
  certificateScope?: 'admin' | 'member'
}) {
  return (
    <div className="cert-detail">
      <div className="cert-detail__head">
        <CertificationStatusChip status={detail.status} />
        {detail.changed_since_review ? (
          <span className="chip chip--warn">Changed since review</span>
        ) : null}
        <span className="cert-detail__version">Snapshot v{detail.snapshot_version}</span>
      </div>

      <dl className="cert-meta">
        <div>
          <dt>Work</dt>
          <dd>{detail.work.title}</dd>
        </div>
        {showMember ? (
          <div>
            <dt>Member</dt>
            <dd>
              {detail.member.name} <span className="mono">{detail.member.member_id}</span>
            </dd>
          </div>
        ) : null}
        <div>
          <dt>Submitted</dt>
          <dd>{formatDateTime(detail.submitted_at)}</dd>
        </div>
        <div>
          <dt>Decided</dt>
          <dd>{formatDateTime(detail.decided_at)}</dd>
        </div>
      </dl>

      {detail.latest_feedback ? (
        <div className="cert-detail__feedback">
          <p className="cert-detail__feedback-label">Latest reviewer feedback</p>
          <p>{detail.latest_feedback}</p>
        </div>
      ) : null}

      <section className="cert-detail__section" aria-label="Submitted snapshot">
        <h2 className="cert-detail__section-title">Submitted snapshot</h2>
        <CertificationSnapshotView snapshot={detail.snapshot} />
      </section>

      {detail.certificate && certificateScope ? (
        <CertificateRefSection certificate={detail.certificate} scope={certificateScope} />
      ) : null}

      <section className="cert-detail__section" aria-label="Decision history">
        <h2 className="cert-detail__section-title">Decision history</h2>
        <DecisionHistory decisions={detail.decisions} />
      </section>
    </div>
  )
}
