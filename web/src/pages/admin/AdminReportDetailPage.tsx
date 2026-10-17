/**
 * Admin report review — reads a member progress report and records a review
 * decision (approve / request changes). `request_changes` requires feedback,
 * and every decision is appended to the report's review history so the full
 * trail (including prior decisions) is preserved across resubmissions.
 *
 * Decisions are restricted to admin-level roles (`require_role("admin")` in the
 * backend); editors see the content but cannot decide.
 */

import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAdminReport } from '../../features/reports/hooks'
import { decideAdminReport } from '../../features/reports/api'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage, isApiError } from '../../lib/errors/ApiError'
import { useAuth } from '../../app/providers/AuthProvider'
import { can } from '../../features/auth/rbac'
import {
  REPORT_DECISION_FEEDBACK_ACTIONS,
  REPORT_DECISION_LABELS,
} from '../../features/reports/labels'
import { ReportStatusChip } from '../../components/reports/ReportStatusChip'
import { EvidenceLinks } from '../../components/reports/EvidenceLinks'
import { ReviewHistory } from '../../components/reports/ReviewHistory'
import { PageHeader } from '../../components/admin/PageHeader'
import { FormField } from '../../components/form/FormField'
import { Textarea } from '../../components/form/Textarea'
import { SaveButton } from '../../components/form/SaveButton'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { NotFoundState } from '../../components/ui/NotFoundState'
import type { ReportDecisionAction } from '../../types/report'

const ACTION_ORDER: ReportDecisionAction[] = ['approve', 'request_changes']

function formatDate(value: string | null): string {
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

export default function AdminReportDetailPage() {
  const { reportId } = useParams<{ reportId: string }>()
  usePageMeta({ title: 'Report review — Admin — Thridha Labs' })

  const { user } = useAuth()
  const mayManage = can(user?.role, 'admin')

  const { data, loading, error, reload } = useAdminReport(reportId)
  useAdminSessionIssue(error)

  const [action, setAction] = useState<ReportDecisionAction | ''>('')
  const [feedback, setFeedback] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [decisionError, setDecisionError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  async function handleDecision(): Promise<void> {
    if (!reportId || !action) return
    setDecisionError(null)
    setNotice(null)

    const trimmedFeedback = feedback.trim()
    if (REPORT_DECISION_FEEDBACK_ACTIONS.includes(action) && !trimmedFeedback) {
      setDecisionError('Feedback is required when requesting changes.')
      return
    }

    setSubmitting(true)
    try {
      await decideAdminReport(reportId, { action, feedback: trimmedFeedback || null })
      setNotice('Decision recorded.')
      setFeedback('')
      setAction('')
      await reload()
    } catch (caught) {
      setDecisionError(getErrorMessage(caught, 'Could not record the decision.'))
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <ContentSkeleton rows={6} />
  if (error) {
    if (isApiError(error) && error.status === 404) return <NotFoundState />
    return <ErrorState error={error} onRetry={reload} />
  }
  if (!data) return <NotFoundState />

  const isPending = data.status === 'pending'
  const feedbackRequired = action !== '' && REPORT_DECISION_FEEDBACK_ACTIONS.includes(action)

  return (
    <div>
      <PageHeader eyebrow="Review" title={data.activity_title}>
        <p className="admin-page-header__description">
          <Link to="/admin/reports">← Back to progress reports</Link>
        </p>
      </PageHeader>

      <div className="cert-review">
        <div className="report-detail">
          <section className="admin-section">
            <h2 className="admin-section__title">Report</h2>
            <div className="report-card__head">
              <ReportStatusChip status={data.status} />
              <span className="report-card__meta mono">
                v{data.version} · submitted {formatDate(data.submitted_at)}
                {data.reviewed_at ? ` · reviewed ${formatDate(data.reviewed_at)}` : ''}
              </span>
            </div>
            <p className="report-card__desc">{data.description}</p>
            <EvidenceLinks links={data.evidence_links} />
          </section>

          <section className="admin-section">
            <h2 className="admin-section__title">Author &amp; project</h2>
            <dl className="member-meta member-meta--stacked">
              <div className="member-meta__row">
                <dt>Member</dt>
                <dd>
                  {data.member_name}
                  <span className="mono"> · {data.member_readable_id}</span>
                  {data.member_email ? (
                    <span className="admin-table__sub">{data.member_email}</span>
                  ) : null}
                </dd>
              </div>
              <div className="member-meta__row">
                <dt>Project</dt>
                <dd>
                  <Link className="admin-table__name" to={`/admin/activities/${data.activity_id}`}>
                    {data.activity_title}
                  </Link>
                </dd>
              </div>
              <div className="member-meta__row">
                <dt>Role</dt>
                <dd>{data.role ?? '—'}</dd>
              </div>
              <div className="member-meta__row">
                <dt>Last updated</dt>
                <dd>{formatDate(data.updated_at)}</dd>
              </div>
            </dl>
          </section>

          <ReviewHistory history={data.review_history} />
        </div>

        <aside className="cert-review__panel" aria-label="Review decision">
          {!mayManage ? (
            <p className="cert-review__note">
              Only admins and owners can record review decisions.
            </p>
          ) : isPending ? (
            <>
              <h2 className="cert-review__title">Record a decision</h2>
              <div className="cert-review__actions" role="radiogroup" aria-label="Decision action">
                {ACTION_ORDER.map((option) => (
                  <label
                    key={option}
                    className={`cert-review__option${action === option ? ' is-selected' : ''}`}
                  >
                    <input
                      type="radio"
                      name="report-review-action"
                      value={option}
                      checked={action === option}
                      onChange={() => {
                        setAction(option)
                        setNotice(null)
                        setDecisionError(null)
                      }}
                    />
                    <span>{REPORT_DECISION_LABELS[option]}</span>
                  </label>
                ))}
              </div>

              <FormField
                id="report-review-feedback"
                label="Feedback"
                hint={feedbackRequired ? 'Required' : 'Optional'}
              >
                <Textarea
                  id="report-review-feedback"
                  rows={5}
                  value={feedback}
                  onChange={(value) => {
                    setFeedback(value)
                    setDecisionError(null)
                  }}
                  placeholder="Notes for the member…"
                />
              </FormField>

              {decisionError ? (
                <p className="form-field__error form-field__error--form" role="alert">
                  {decisionError}
                </p>
              ) : null}

              <SaveButton
                busy={submitting}
                busyLabel="Saving…"
                disabled={!action}
                onClick={() => void handleDecision()}
              >
                Submit decision
              </SaveButton>
            </>
          ) : (
            <p className="cert-review__note">
              This report is not awaiting review.
              {data.review_feedback ? ` Reviewer feedback: ${data.review_feedback}` : ''}
            </p>
          )}

          {notice ? (
            <p className="admin-form__dirty" role="status">
              {notice}
            </p>
          ) : null}
        </aside>
      </div>
    </div>
  )
}
