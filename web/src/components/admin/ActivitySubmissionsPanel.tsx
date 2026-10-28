/**
 * ActivitySubmissionsPanel — admin review of the individual work submitted in
 * one programme/hackathon.
 *
 * Every student owns their own progress updates and at most one deliverable,
 * so the queue is a flat list of submissions with an approve / request-changes
 * / reject decision on each. Decisions are appended to the submission's review
 * history by the backend and can never be edited away.
 */

import { useState } from 'react'
import { Select } from '../form/Select'
import { Textarea } from '../form/Textarea'
import { SaveButton } from '../form/SaveButton'
import { ContentSkeleton } from '../ui/ContentSkeleton'
import { EmptyState } from '../ui/EmptyState'
import { ErrorState } from '../ui/ErrorState'
import { useAdminActivitySubmissionsForActivity } from '../../features/activityWorkspaces/hooks'
import { decideAdminActivitySubmission } from '../../features/activityWorkspaces/api'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { ACTIVITY_SUBMISSION_STATUS_LABELS } from '../../types/activitySubmission'
import type {
  ActivitySubmissionDecisionAction,
  ActivitySubmissionKind,
  ActivitySubmissionStatus,
  AdminActivitySubmission,
} from '../../types/activitySubmission'

const STATUS_OPTIONS = (
  Object.keys(ACTIVITY_SUBMISSION_STATUS_LABELS) as ActivitySubmissionStatus[]
).map((value) => ({ value, label: ACTIVITY_SUBMISSION_STATUS_LABELS[value] }))

const KIND_OPTIONS: { value: ActivitySubmissionKind; label: string }[] = [
  { value: 'deliverable', label: 'Deliverable' },
  { value: 'progress_update', label: 'Progress update' },
]

/** Decisions that require the reviewer to explain what must change. */
const FEEDBACK_REQUIRED: ActivitySubmissionDecisionAction[] = ['request_changes']

function formatDateTime(value: string | null): string {
  if (!value) return '—'
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

function SubmissionRow({
  submission,
  onDecided,
}: {
  submission: AdminActivitySubmission
  onDecided: () => void
}) {
  const [action, setAction] = useState<ActivitySubmissionDecisionAction>('approve')
  const [feedback, setFeedback] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const needsFeedback = FEEDBACK_REQUIRED.includes(action)
  const final = submission.status === 'approved' || submission.status === 'rejected'

  async function decide(): Promise<void> {
    setBusy(true)
    setError(null)
    try {
      await decideAdminActivitySubmission(submission.id, {
        action,
        feedback: feedback.trim() || null,
      })
      setFeedback('')
      onDecided()
    } catch (caught) {
      setError(getErrorMessage(caught, 'Could not record the decision.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="workspace-review__row">
      <div className="workspace-review__row-head">
        <div className="workspace-review__author">
          <span className="workspace-review__author-name">
            {submission.member_name ?? submission.member_readable_id}
          </span>
          <span className="workspace-review__author-meta">
            {submission.member_readable_id}
            {submission.member_email ? ` · ${submission.member_email}` : ''}
          </span>
        </div>
        <div className="member-activity-card__meta">
          <span className={`chip chip--${submission.status === 'approved' ? 'ok' : submission.status === 'rejected' ? 'danger' : submission.status === 'changes_requested' ? 'warn' : 'admin'}`}>
            {ACTIVITY_SUBMISSION_STATUS_LABELS[submission.status]}
          </span>
          <span className="chip">
            {submission.kind === 'deliverable' ? 'Deliverable' : 'Progress update'}
          </span>
          <span className="workspace__submission-meta">v{submission.version}</span>
        </div>
      </div>

      {submission.title ? <p className="workspace__task-title">{submission.title}</p> : null}
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

      <span className="workspace__submission-meta">
        Submitted {formatDateTime(submission.submitted_at)}
        {submission.reviewed_at ? ` · Last reviewed ${formatDateTime(submission.reviewed_at)}` : ''}
      </span>

      {submission.review_history.length > 0 ? (
        <details className="workspace__section">
          <summary className="workspace__section-title">
            Review history ({submission.review_history.length})
          </summary>
          <ol className="report-history__list">
            {[...submission.review_history]
              .sort((a, b) => (a.decided_at < b.decided_at ? 1 : a.decided_at > b.decided_at ? -1 : 0))
              .map((entry, index) => (
                <li key={`${entry.decided_at}-${index}`} className="report-history__item">
                  <div className="report-history__head">
                    <span className="workspace__submission-meta">
                      {ACTIVITY_SUBMISSION_STATUS_LABELS[entry.status]} · v{entry.version} ·{' '}
                      {entry.reviewer_name ?? 'Reviewer'} · {formatDateTime(entry.decided_at)}
                    </span>
                  </div>
                  {entry.feedback ? (
                    <p className="report-history__feedback">{entry.feedback}</p>
                  ) : null}
                </li>
              ))}
          </ol>
        </details>
      ) : null}

      {final ? (
        <p className="admin-section__hint">
          This submission is final. Approved and rejected work cannot be edited by the student.
        </p>
      ) : (
        <div className="workspace-review">
          <div className="workspace-review__actions">
            <Select
              aria-label={`Decision for ${submission.member_readable_id}`}
              options={[
                { value: 'approve', label: 'Approve' },
                { value: 'request_changes', label: 'Request changes' },
                { value: 'reject', label: 'Reject' },
              ]}
              value={action}
              onChange={(value) => setAction(value as ActivitySubmissionDecisionAction)}
            />
            <SaveButton busy={busy} onClick={() => void decide()}>
              Record decision
            </SaveButton>
          </div>

          {needsFeedback ? (
            <div className="workspace-review__feedback">
              <Textarea
                aria-label={`Feedback for ${submission.member_readable_id}`}
                rows={3}
                value={feedback}
                onChange={setFeedback}
                placeholder="What should the student change?"
              />
              <p className="admin-section__hint">Feedback is required to request changes.</p>
            </div>
          ) : (
            <div className="workspace-review__feedback">
              <Textarea
                aria-label={`Feedback for ${submission.member_readable_id}`}
                rows={2}
                value={feedback}
                onChange={setFeedback}
                placeholder="Optional feedback"
              />
            </div>
          )}

          {error ? (
            <p className="form-field__error" role="alert">
              {error}
            </p>
          ) : null}
        </div>
      )}
    </div>
  )
}

export interface ActivitySubmissionsPanelProps {
  activityId: string
}

export function ActivitySubmissionsPanel({ activityId }: ActivitySubmissionsPanelProps) {
  const [statusFilter, setStatusFilter] = useState<'' | ActivitySubmissionStatus>('')
  const [kindFilter, setKindFilter] = useState<'' | ActivitySubmissionKind>('')

  const { data, loading, error, reload } = useAdminActivitySubmissionsForActivity(activityId, {
    page: 1,
    page_size: 100,
    status: statusFilter || undefined,
    kind: kindFilter || undefined,
  })

  const items = data?.items ?? []

  return (
    <section className="admin-section">
      <div className="admin-section__head">
        <h2 className="admin-section__title">Submissions</h2>
        <div className="workspace-review__actions">
          <Select
            aria-label="Filter submissions by status"
            placeholder="All statuses"
            options={STATUS_OPTIONS}
            value={statusFilter}
            onChange={(value) => setStatusFilter(value as '' | ActivitySubmissionStatus)}
          />
          <Select
            aria-label="Filter submissions by kind"
            placeholder="All types"
            options={KIND_OPTIONS}
            value={kindFilter}
            onChange={(value) => setKindFilter(value as '' | ActivitySubmissionKind)}
          />
        </div>
      </div>

      {loading && items.length === 0 ? <ContentSkeleton rows={3} /> : null}
      {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}
      {!loading && !error && items.length === 0 ? (
        <EmptyState
          title="No submissions yet"
          description="Progress updates and deliverables from confirmed participants will appear here."
        />
      ) : null}

      {items.length > 0 ? (
        <div className="workspace-review">
          {items.map((submission) => (
            <SubmissionRow key={submission.id} submission={submission} onDecided={reload} />
          ))}
        </div>
      ) : null}

      <p className="admin-section__hint">
        Participation is individual — each student owns their own work. Approving or rejecting a
        submission is final.
      </p>
    </section>
  )
}
