/**
 * Admin work review — reads a member-submitted work and records a publication
 * decision (approve / request changes / reject). Approved, public works can
 * additionally be featured on the official Projects page with a display
 * classification. Both actions are restricted to admin-level roles.
 */

import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAdminWork } from '../../features/works/hooks'
import { decideAdminWork, setAdminWorkFeatured } from '../../features/works/api'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage, isApiError } from '../../lib/errors/ApiError'
import { useAuth } from '../../app/providers/AuthProvider'
import { can } from '../../features/auth/rbac'
import {
  WORK_REVIEW_ACTION_LABELS,
  WORK_REVIEW_FEEDBACK_ACTIONS,
  WORK_STATUS_CHIP,
  WORK_STATUS_LABELS,
} from '../../features/works/status'
import { PROJECT_TYPE_LABELS } from '../../components/public/labels'
import { ContentRenderer } from '../../components/works/ContentRenderer'
import { PageHeader } from '../../components/admin/PageHeader'
import { FormField } from '../../components/form/FormField'
import { Textarea } from '../../components/form/Textarea'
import { Select } from '../../components/form/Select'
import { SaveButton } from '../../components/form/SaveButton'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { NotFoundState } from '../../components/ui/NotFoundState'
import type { ProjectType } from '../../types/content'
import type { WorkReviewAction } from '../../types/work'

const ACTION_ORDER: WorkReviewAction[] = ['approve', 'request_changes', 'reject']

export default function AdminWorkDetailPage() {
  const { workId } = useParams<{ workId: string }>()
  usePageMeta({ title: 'Work review — Admin — Thridha Labs' })

  const { user } = useAuth()
  const mayManage = can(user?.role, 'admin')

  const { data, loading, error, reload } = useAdminWork(workId)
  useAdminSessionIssue(error)

  const [action, setAction] = useState<WorkReviewAction | ''>('')
  const [feedback, setFeedback] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [decisionError, setDecisionError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const [featured, setFeatured] = useState(true)
  const [classification, setClassification] = useState<ProjectType>('member-contribution')
  const [featureBusy, setFeatureBusy] = useState(false)
  const [featureError, setFeatureError] = useState<string | null>(null)

  async function handleDecision(): Promise<void> {
    if (!workId || !action) return
    setDecisionError(null)
    setNotice(null)

    if (WORK_REVIEW_FEEDBACK_ACTIONS.includes(action) && !feedback.trim()) {
      setDecisionError('Feedback is required when requesting changes or rejecting.')
      return
    }

    setSubmitting(true)
    try {
      await decideAdminWork(workId, { action, feedback: feedback.trim() || null })
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

  async function handleFeature(): Promise<void> {
    if (!workId) return
    setFeatureError(null)
    setNotice(null)
    setFeatureBusy(true)
    try {
      await setAdminWorkFeatured(workId, { featured, classification })
      setNotice(featured ? 'Featured on the Projects page.' : 'Removed from the Projects page.')
      await reload()
    } catch (caught) {
      setFeatureError(getErrorMessage(caught, 'Could not update featuring.'))
    } finally {
      setFeatureBusy(false)
    }
  }

  if (loading) return <ContentSkeleton rows={6} />
  if (error) {
    if (isApiError(error) && error.status === 404) return <NotFoundState />
    return <ErrorState error={error} onRetry={reload} />
  }
  if (!data) return <NotFoundState />

  const isPending = data.publication_status === 'pending_review'
  const isPublished = data.publication_status === 'published'
  const canFeature = isPublished && data.visibility === 'public'

  return (
    <div>
      <PageHeader eyebrow="Review" title={data.title}>
        <p className="admin-page-header__description">
          <Link to="/admin/works">← Back to publication review</Link>
        </p>
      </PageHeader>

      <div className="cert-review">
        <div className="works-review__main">
          <div className="works-review__meta">
            <span className={`chip ${WORK_STATUS_CHIP[data.publication_status]}`}>
              {WORK_STATUS_LABELS[data.publication_status]}
            </span>
            <span className="chip">{data.visibility}</span>
            {data.featured_on_projects ? <span className="chip chip--ok">Featured</span> : null}
            <span className="admin-table__sub mono">
              {data.member_name} · {data.member_id}
            </span>
          </div>

          <p className="work-public__summary">{data.summary}</p>
          <ContentRenderer document={data.content} />
        </div>

        <aside className="cert-review__panel" aria-label="Review decision">
          {!mayManage ? (
            <p className="cert-review__note">
              Only admins and owners can record publication decisions.
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
                      name="work-review-action"
                      value={option}
                      checked={action === option}
                      onChange={() => {
                        setAction(option)
                        setNotice(null)
                      }}
                    />
                    <span>{WORK_REVIEW_ACTION_LABELS[option]}</span>
                  </label>
                ))}
              </div>

              <FormField
                id="work-review-feedback"
                label="Feedback"
                hint={
                  action && WORK_REVIEW_FEEDBACK_ACTIONS.includes(action) ? 'Required' : 'Optional'
                }
              >
                <Textarea
                  id="work-review-feedback"
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

              <SaveButton busy={submitting} disabled={!action} onClick={() => void handleDecision()}>
                Submit decision
              </SaveButton>
            </>
          ) : (
            <p className="cert-review__note">
              {isPublished
                ? 'This work has been published.'
                : 'This work is not awaiting review.'}
              {data.review_feedback ? ` Reviewer feedback: ${data.review_feedback}` : ''}
            </p>
          )}

          {mayManage && isPublished ? (
            <div className="works-review__feature">
              <h2 className="cert-review__title">Official Projects page</h2>
              {canFeature ? (
                <>
                  <FormField id="work-feature-classification" label="Classification">
                    <Select
                      id="work-feature-classification"
                      options={Object.entries(PROJECT_TYPE_LABELS).map(([value, label]) => ({
                        value,
                        label,
                      }))}
                      value={classification}
                      onChange={(value) => setClassification(value as ProjectType)}
                    />
                  </FormField>
                  <div className="cert-review__actions" role="radiogroup" aria-label="Featuring">
                    <label className={`cert-review__option${featured ? ' is-selected' : ''}`}>
                      <input
                        type="radio"
                        name="work-feature"
                        checked={featured}
                        onChange={() => setFeatured(true)}
                      />
                      <span>Feature</span>
                    </label>
                    <label className={`cert-review__option${!featured ? ' is-selected' : ''}`}>
                      <input
                        type="radio"
                        name="work-feature"
                        checked={!featured}
                        onChange={() => setFeatured(false)}
                      />
                      <span>Remove</span>
                    </label>
                  </div>
                  {featureError ? (
                    <p className="form-field__error form-field__error--form" role="alert">
                      {featureError}
                    </p>
                  ) : null}
                  <SaveButton busy={featureBusy} onClick={() => void handleFeature()}>
                    {featured ? 'Save featuring' : 'Remove featuring'}
                  </SaveButton>
                </>
              ) : (
                <p className="cert-review__note">
                  Only published, public-visible works can be featured on the official Projects page.
                </p>
              )}
            </div>
          ) : null}

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
