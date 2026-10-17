/**
 * Admin certification detail — reviews the frozen snapshot of a work and
 * records a decision. Decisions are restricted to admin-level roles; editors
 * can read the request but cannot decide.
 */

import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAdminCertification } from '../../features/certifications/hooks'
import { decideCertification } from '../../features/certifications/api'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { useAuth } from '../../app/providers/AuthProvider'
import { can } from '../../features/auth/rbac'
import {
  CERTIFICATION_ACTION_LABELS,
  CERTIFICATION_FEEDBACK_ACTIONS,
} from '../../features/certifications/status'
import { CertificationDetailPanel } from '../../components/certifications/CertificationDetailPanel'
import { CertificatePanel } from '../../components/certificates/CertificatePanel'
import { PageHeader } from '../../components/admin/PageHeader'
import { FormField } from '../../components/form/FormField'
import { Textarea } from '../../components/form/Textarea'
import { SaveButton } from '../../components/form/SaveButton'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { NotFoundState } from '../../components/ui/NotFoundState'
import { isApiError } from '../../lib/errors/ApiError'
import type { CertificationReviewAction } from '../../types/certification'

const ACTION_ORDER: CertificationReviewAction[] = ['under_review', 'approve', 'request_changes', 'reject']

export default function AdminCertificationDetailPage() {
  const { requestId } = useParams<{ requestId: string }>()
  usePageMeta({ title: 'Certification review — Admin — Thridha Labs' })

  const { user } = useAuth()
  const mayDecide = can(user?.role, 'admin')

  const { data, loading, error, reload } = useAdminCertification(requestId)
  useAdminSessionIssue(error)

  const [action, setAction] = useState<CertificationReviewAction | ''>('')
  const [feedback, setFeedback] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [decisionError, setDecisionError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  async function handleDecision(): Promise<void> {
    if (!requestId || !action) return
    setDecisionError(null)
    setNotice(null)

    if (CERTIFICATION_FEEDBACK_ACTIONS.includes(action) && !feedback.trim()) {
      setDecisionError('Feedback is required when requesting changes or rejecting.')
      return
    }

    setSubmitting(true)
    try {
      await decideCertification(requestId, {
        action,
        feedback: feedback.trim() || null,
      })
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

  const decidable = data.status === 'submitted' || data.status === 'under_review'
  const awaitingResubmit = data.status === 'changes_requested'

  return (
    <div>
      <PageHeader eyebrow="Review" title={data.work.title}>
        <p className="admin-page-header__description">
          <Link to="/admin/certifications">← Back to certifications</Link>
        </p>
      </PageHeader>

      <div className="cert-review">
        <CertificationDetailPanel detail={data} showMember />

        <aside className="cert-review__panel" aria-label="Review decision">
          {!mayDecide ? (
            <p className="cert-review__note">
              Only admins and owners can record certification decisions.
            </p>
          ) : !decidable ? (
            <p className="cert-review__note">
              {awaitingResubmit
                ? 'Changes were requested — awaiting the member’s resubmission.'
                : 'This request has been decided.'}
            </p>
          ) : (
            <>
              <h2 className="cert-review__title">Record a decision</h2>
              <div className="cert-review__actions" role="radiogroup" aria-label="Decision action">
                {ACTION_ORDER.map((option) => (
                  <label key={option} className={`cert-review__option${action === option ? ' is-selected' : ''}`}>
                    <input
                      type="radio"
                      name="cert-action"
                      value={option}
                      checked={action === option}
                      onChange={() => {
                        setAction(option)
                        setNotice(null)
                      }}
                    />
                    <span>{CERTIFICATION_ACTION_LABELS[option]}</span>
                  </label>
                ))}
              </div>

              <FormField
                id="cert-feedback"
                label="Feedback"
                hint={
                  action && CERTIFICATION_FEEDBACK_ACTIONS.includes(action)
                    ? 'Required'
                    : 'Optional'
                }
              >
                <Textarea
                  id="cert-feedback"
                  rows={5}
                  value={feedback}
                  onChange={setFeedback}
                  placeholder="Notes for the member…"
                />
              </FormField>

              {decisionError ? (
                <p className="form-field__error form-field__error--form" role="alert">
                  {decisionError}
                </p>
              ) : null}
              {notice ? (
                <p className="admin-form__dirty" role="status">
                  {notice}
                </p>
              ) : null}

              <SaveButton
                busy={submitting}
                disabled={!action}
                onClick={() => void handleDecision()}
              >
                Submit decision
              </SaveButton>
            </>
          )}

          {mayDecide ? (
            <CertificatePanel
              requestId={data.id}
              requestStatus={data.status}
              certificateId={data.certificate?.certificate_id ?? null}
              canManage={mayDecide}
              onChanged={reload}
            />
          ) : null}
        </aside>
      </div>
    </div>
  )
}
