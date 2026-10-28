/**
 * ActivitySubmissionCard — read-only view of one of the member's submissions.
 *
 * Shows the current content, its review status, the latest admin feedback and
 * the full review trail. Editing is driven by the parent (it decides whether
 * the submission is still editable).
 */

import { ActivitySubmissionStatusChip } from './ActivitySubmissionStatusChip'
import type { ActivitySubmission } from '../../types/activitySubmission'

export interface ActivitySubmissionCardProps {
  submission: ActivitySubmission
  onEdit?: (submission: ActivitySubmission) => void
}

function formatDateTime(value: string): string {
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

export function ActivitySubmissionCard({ submission, onEdit }: ActivitySubmissionCardProps) {
  const entries = [...submission.review_history].sort((a, b) =>
    a.decided_at < b.decided_at ? 1 : a.decided_at > b.decided_at ? -1 : 0,
  )

  return (
    <article className="workspace__submission">
      <header className="workspace__submission-head">
        <ActivitySubmissionStatusChip status={submission.status} />
        <span className="workspace__submission-meta">
          v{submission.version} · {submission.kind === 'deliverable' ? 'Deliverable' : 'Progress update'}
        </span>
        <span className="workspace__submission-meta">
          Submitted {formatDateTime(submission.submitted_at)}
        </span>
      </header>

      {submission.title ? <h3 className="workspace__task-title">{submission.title}</h3> : null}

      <p className="workspace__text">{submission.description}</p>

      {submission.repository_url || submission.demo_url || submission.evidence_links.length > 0 ? (
        <div className="workspace__submission-links">
          {submission.repository_url ? (
            <span>
              Repository:{' '}
              <a href={submission.repository_url} target="_blank" rel="noreferrer">
                {submission.repository_url}
              </a>
            </span>
          ) : null}
          {submission.demo_url ? (
            <span>
              Demo:{' '}
              <a href={submission.demo_url} target="_blank" rel="noreferrer">
                {submission.demo_url}
              </a>
            </span>
          ) : null}
          {submission.evidence_links.map((link) => (
            <span key={link}>
              Evidence:{' '}
              <a href={link} target="_blank" rel="noreferrer">
                {link}
              </a>
            </span>
          ))}
        </div>
      ) : null}

      {submission.review_feedback ? (
        <p className="report-card__feedback">{submission.review_feedback}</p>
      ) : null}

      {entries.length > 0 ? (
        <div className="report-history">
          <p className="report-history__label">Review history</p>
          <ol className="report-history__list">
            {entries.map((entry, index) => (
              <li key={`${entry.decided_at}-${index}`} className="report-history__item">
                <div className="report-history__head">
                  <ActivitySubmissionStatusChip status={entry.status} />
                  <span className="report-history__meta mono">
                    {entry.reviewer_name ?? 'Reviewer'} · reviewed v{entry.version} ·{' '}
                    {formatDateTime(entry.decided_at)}
                  </span>
                </div>
                {entry.feedback ? (
                  <p className="report-history__feedback">{entry.feedback}</p>
                ) : null}
              </li>
            ))}
          </ol>
        </div>
      ) : null}

      {submission.revisions.length > 0 ? (
        <details className="workspace__section">
          <summary className="workspace__section-title">
            Previous versions ({submission.revisions.length})
          </summary>
          {submission.revisions.map((revision) => (
            <div key={revision.version} className="workspace__section">
              <p className="workspace__submission-meta">
                v{revision.version} · {formatDateTime(revision.submitted_at)}
              </p>
              <p className="workspace__text">{revision.description}</p>
            </div>
          ))}
        </details>
      ) : null}

      {onEdit && submission.editable ? (
        <div className="workspace__submission-actions">
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => onEdit(submission)}
          >
            Edit & resubmit
          </button>
        </div>
      ) : null}
    </article>
  )
}
