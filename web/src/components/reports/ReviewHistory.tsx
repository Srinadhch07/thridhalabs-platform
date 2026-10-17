/**
 * ReviewHistory — the immutable trail of admin decisions on a report.
 *
 * Every decision is appended by the backend (never overwritten), so this list
 * survives a member's edit-and-resubmit. Each entry records which content
 * `version` was reviewed, so a member can tell whether they have edited since
 * the last decision.
 */

import { REPORT_STATUS_LABELS } from '../../features/reports/labels'
import { ReportStatusChip } from './ReportStatusChip'
import type { ReportReviewEntry } from '../../types/report'

function formatDecidedAt(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function ReviewHistory({ history }: { history: ReportReviewEntry[] }) {
  if (history.length === 0) return null
  // Newest decision first.
  const entries = [...history].sort((a, b) =>
    a.decided_at < b.decided_at ? 1 : a.decided_at > b.decided_at ? -1 : 0,
  )

  return (
    <div className="report-history">
      <p className="report-history__label">Review history</p>
      <ol className="report-history__list">
        {entries.map((entry, index) => (
          <li key={`${entry.decided_at}-${index}`} className="report-history__item">
            <div className="report-history__head">
              <ReportStatusChip status={entry.status} />
              <span className="report-history__meta mono">
                {entry.reviewer_name ?? 'Reviewer'} · {REPORT_STATUS_LABELS[entry.status]} ·
                reviewed v{entry.version} · {formatDecidedAt(entry.decided_at)}
              </span>
            </div>
            {entry.feedback ? (
              <p className="report-history__feedback">{entry.feedback}</p>
            ) : null}
          </li>
        ))}
      </ol>
    </div>
  )
}
