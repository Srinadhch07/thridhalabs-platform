/**
 * Member activity workspace — the individual workspace for one programme or
 * hackathon the member has joined.
 *
 * Participation is individual: the checklist, the deliverable and every progress
 * update belong to the signed-in member only. There is no team surface here.
 *
 * The page is read from `/member/activity-workspaces/{slug}`; all mutations go
 * through the member submission/task endpoints, which resolve ownership
 * server-side.
 */

import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMyActivityWorkspace } from '../../features/activityWorkspaces/hooks'
import {
  createActivitySubmission,
  setActivityTaskCompletion,
  updateActivitySubmission,
} from '../../features/activityWorkspaces/api'
import { useMemberSessionIssue } from '../../lib/hooks/useMemberSession'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage } from '../../lib/errors/ApiError'
import {
  ACTIVITY_TYPE_LABELS,
  PRESENTATION_LABELS,
  formatSchedule,
} from '../../features/activities/labels'
import { MemberPageHeader } from '../../components/member/MemberPageHeader'
import { MemberEmptyState } from '../../components/member/MemberEmptyState'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { NotFoundState } from '../../components/ui/NotFoundState'
import { ActivitySubmissionForm } from '../../components/workspaces/ActivitySubmissionForm'
import type { ActivitySubmissionFormValues } from '../../components/workspaces/ActivitySubmissionForm'
import { ActivitySubmissionCard } from '../../components/workspaces/ActivitySubmissionCard'
import { ActivityTaskChecklist } from '../../components/workspaces/ActivityTaskChecklist'
import { REQUIRED_DELIVERABLE_LABELS } from '../../types/activitySubmission'
import type {
  ActivitySubmission,
  ActivitySubmissionKind,
  ActivityWorkspace,
} from '../../types/activitySubmission'

/** Idempotency key so a retried submit cannot create a duplicate. */
function newRequestId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `submission-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

interface SubmissionEditorProps {
  workspace: ActivityWorkspace
  kind: ActivitySubmissionKind
  submission: ActivitySubmission | null
  busy: boolean
  error: string | null
  onCancel: () => void
  onSubmit: (values: ActivitySubmissionFormValues) => void
}

function SubmissionEditor({
  workspace,
  kind,
  submission,
  busy,
  error,
  onCancel,
  onSubmit,
}: SubmissionEditorProps) {
  return (
    <ActivitySubmissionForm
      idPrefix={submission ? `submission-edit-${submission.id}` : `submission-new-${kind}`}
      kind={kind}
      requiredDeliverables={workspace.required_deliverables}
      busy={busy}
      error={error}
      initial={submission}
      submitLabel={
        submission
          ? 'Resubmit for review'
          : kind === 'deliverable'
            ? 'Submit deliverable'
            : 'Post update'
      }
      onCancel={onCancel}
      onSubmit={onSubmit}
    />
  )
}

export default function MemberActivityWorkspacePage() {
  const { slug } = useParams<{ slug: string }>()
  usePageMeta({ title: 'Activity workspace — Member portal — Thridha Labs' })

  const workspaceState = useMyActivityWorkspace(slug)
  useMemberSessionIssue(workspaceState.error)

  const [taskBusyId, setTaskBusyId] = useState<string | null>(null)
  const [taskError, setTaskError] = useState<string | null>(null)

  const [editorKind, setEditorKind] = useState<ActivitySubmissionKind | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [submitBusy, setSubmitBusy] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const workspace = workspaceState.data

  async function handleToggleTask(taskId: string, completed: boolean): Promise<void> {
    if (!workspace) return
    setTaskBusyId(taskId)
    setTaskError(null)
    try {
      await setActivityTaskCompletion(workspace.slug, { task_id: taskId, completed })
      workspaceState.reload()
    } catch (caught) {
      setTaskError(getErrorMessage(caught, 'Could not update the task.'))
    } finally {
      setTaskBusyId(null)
    }
  }

  async function handleCreate(
    kind: ActivitySubmissionKind,
    values: ActivitySubmissionFormValues,
  ): Promise<void> {
    if (!workspace) return
    setSubmitBusy(true)
    setSubmitError(null)
    setNotice(null)
    try {
      await createActivitySubmission({
        activity_id: workspace.activity_id,
        kind,
        title: values.title,
        description: values.description,
        repository_url: values.repository_url,
        demo_url: values.demo_url,
        evidence_links: values.evidence_links,
        attachment_media_ids: values.attachment_media_ids,
        client_request_id: newRequestId(),
      })
      setEditorKind(null)
      setNotice(
        kind === 'deliverable'
          ? 'Deliverable submitted for review.'
          : 'Progress update posted.',
      )
      workspaceState.reload()
    } catch (caught) {
      setSubmitError(getErrorMessage(caught, 'Could not submit your work.'))
    } finally {
      setSubmitBusy(false)
    }
  }

  async function handleUpdate(
    submissionId: string,
    values: ActivitySubmissionFormValues,
  ): Promise<void> {
    setSubmitBusy(true)
    setSubmitError(null)
    setNotice(null)
    try {
      await updateActivitySubmission(submissionId, {
        title: values.title,
        description: values.description,
        repository_url: values.repository_url,
        demo_url: values.demo_url,
        evidence_links: values.evidence_links,
        attachment_media_ids: values.attachment_media_ids,
      })
      setEditingId(null)
      setNotice('Resubmitted for review.')
      workspaceState.reload()
    } catch (caught) {
      setSubmitError(getErrorMessage(caught, 'Could not update your submission.'))
    } finally {
      setSubmitBusy(false)
    }
  }

  if (workspaceState.loading) return <ContentSkeleton rows={6} />
  if (workspaceState.error) {
    return <ErrorState error={workspaceState.error} onRetry={workspaceState.reload} />
  }
  if (!workspace) return <NotFoundState title="Workspace not found" />

  const deliverable = workspace.deliverable
  const progressUpdates = workspace.progress_updates
  const typeLabel =
    ACTIVITY_TYPE_LABELS[workspace.activity_type as 'programme' | 'hackathon'] ??
    workspace.activity_type

  return (
    <div className="member-page">
      <MemberPageHeader
        eyebrow="My activities"
        title={workspace.title}
        description={workspace.summary || undefined}
        actions={
          <Link className="btn btn--ghost" to="/member/activities">
            ← All activities
          </Link>
        }
      />

      <div className="workspace">
        <div className="member-activity-card__meta">
          <span className="chip">{typeLabel}</span>
          <span className={`chip chip--activity chip--activity-${workspace.presentation_status}`}>
            {PRESENTATION_LABELS[workspace.presentation_status]}
          </span>
          {workspace.participation_status ? (
            <span className="chip chip--part chip--part-confirmed">Confirmed</span>
          ) : null}
          {formatSchedule(workspace.start_date, workspace.end_date) ? (
            <span className="member-activity-card__schedule">
              {formatSchedule(workspace.start_date, workspace.end_date)}
            </span>
          ) : null}
        </div>

        {notice ? (
          <p className="form-field__error form-field__error--form" role="status">
            {notice}
          </p>
        ) : null}
        {taskError ? (
          <p className="form-field__error form-field__error--form" role="alert">
            {taskError}
          </p>
        ) : null}

        {workspace.description ? (
          <section className="member-card">
            <div className="workspace__section">
              <h2 className="workspace__section-title">About this activity</h2>
              <p className="workspace__text">{workspace.description}</p>
            </div>
          </section>
        ) : null}

        {workspace.objectives.length > 0 || workspace.instructions ? (
          <section className="member-card">
            <div className="workspace__section">
              <h2 className="workspace__section-title">Objectives & instructions</h2>
              {workspace.objectives.length > 0 ? (
                <ul className="workspace__list">
                  {workspace.objectives.map((objective, index) => (
                    <li key={`${index}-${objective}`}>{objective}</li>
                  ))}
                </ul>
              ) : null}
              {workspace.instructions ? (
                <p className="workspace__text">{workspace.instructions}</p>
              ) : null}
            </div>
          </section>
        ) : null}

        {workspace.requirements.length > 0 ? (
          <section className="member-card">
            <div className="workspace__section">
              <h2 className="workspace__section-title">Requirements</h2>
              <ul className="workspace__list">
                {workspace.requirements.map((requirement, index) => (
                  <li key={`${index}-${requirement}`}>{requirement}</li>
                ))}
              </ul>
            </div>
          </section>
        ) : null}

        {workspace.resources.length > 0 ? (
          <section className="member-card">
            <div className="workspace__section">
              <h2 className="workspace__section-title">Resources</h2>
              <div className="workspace__resources">
                {workspace.resources.map((resource, index) => (
                  <div className="workspace__resource" key={`${index}-${resource.url}`}>
                    <span className="workspace__resource-label">{resource.label}</span>
                    <a href={resource.url} target="_blank" rel="noreferrer">
                      {resource.url}
                    </a>
                  </div>
                ))}
              </div>
            </div>
          </section>
        ) : null}

        {workspace.required_deliverables.length > 0 ? (
          <section className="member-card">
            <div className="workspace__section">
              <h2 className="workspace__section-title">What to submit</h2>
              <ul className="workspace__required">
                {workspace.required_deliverables.map((part) => (
                  <li className="workspace__required-item" key={part}>
                    {REQUIRED_DELIVERABLE_LABELS[part]}
                  </li>
                ))}
              </ul>
            </div>
          </section>
        ) : null}

        {workspace.tasks.length > 0 ? (
          <section className="member-card">
            <div className="workspace__section">
              <h2 className="workspace__section-title">Your checklist</h2>
              <div className="workspace__progress">
                <div
                  className="workspace__progress-track"
                  role="progressbar"
                  aria-valuenow={workspace.progress_percent}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="Task completion"
                >
                  <span
                    className="workspace__progress-fill"
                    style={{ width: `${workspace.progress_percent}%` }}
                  />
                </div>
                <span className="workspace__progress-value">
                  {workspace.completed_task_count} / {workspace.task_count} tasks ·{' '}
                  {workspace.progress_percent}%
                </span>
              </div>
              <ActivityTaskChecklist
                tasks={workspace.tasks}
                busyTaskId={taskBusyId}
                onToggle={(taskId, completed) => void handleToggleTask(taskId, completed)}
              />
            </div>
          </section>
        ) : null}

        <section className="member-card">
          <div className="member-card__header">
            <div>
              <h2 className="member-card__title">Your deliverable</h2>
              <p className="member-card__desc">
                One deliverable per activity. You can edit and resubmit it until an admin
                approves or rejects it.
              </p>
            </div>
          </div>

          {deliverable && editingId !== deliverable.id ? (
            <ActivitySubmissionCard
              submission={deliverable}
              onEdit={(submission) => {
                setEditingId(submission.id)
                setEditorKind('deliverable')
                setSubmitError(null)
                setNotice(null)
              }}
            />
          ) : null}

          {editorKind === 'deliverable' && editingId === deliverable?.id ? (
            <SubmissionEditor
              workspace={workspace}
              kind="deliverable"
              submission={deliverable}
              busy={submitBusy}
              error={submitError}
              onCancel={() => {
                setEditorKind(null)
                setEditingId(null)
                setSubmitError(null)
              }}
              onSubmit={(values) => void handleUpdate(deliverable.id, values)}
            />
          ) : null}

          {!deliverable && editorKind !== 'deliverable' ? (
            workspace.can_submit ? (
              <SubmissionEditor
                workspace={workspace}
                kind="deliverable"
                submission={null}
                busy={submitBusy}
                error={submitError}
                onCancel={() => {
                  setEditorKind(null)
                  setSubmitError(null)
                }}
                onSubmit={(values) => void handleCreate('deliverable', values)}
              />
            ) : (
              <MemberEmptyState
                title="Deliverable not available"
                description={
                  workspace.submit_blocked_reason ??
                  'Deliverables are not open for this activity right now.'
                }
              />
            )
          ) : null}
        </section>

        <section className="member-card">
          <div className="member-card__header">
            <div>
              <h2 className="member-card__title">Progress updates</h2>
              <p className="member-card__desc">
                Short notes about what you have worked on so far.
              </p>
            </div>
          </div>

          {workspace.can_submit && editorKind !== 'progress_update' ? (
            <div className="workspace__submission-actions">
              <button
                type="button"
                className="btn btn--primary btn--sm"
                onClick={() => {
                  setEditorKind('progress_update')
                  setEditingId(null)
                  setSubmitError(null)
                  setNotice(null)
                }}
              >
                Post an update
              </button>
            </div>
          ) : null}

          {editorKind === 'progress_update' && editingId === null ? (
            <SubmissionEditor
              workspace={workspace}
              kind="progress_update"
              submission={null}
              busy={submitBusy}
              error={submitError}
              onCancel={() => {
                setEditorKind(null)
                setSubmitError(null)
              }}
              onSubmit={(values) => void handleCreate('progress_update', values)}
            />
          ) : null}

          {progressUpdates.length === 0 && editorKind !== 'progress_update' ? (
            <MemberEmptyState
              title="No updates yet"
              description="Post your first update to share what you have worked on."
            />
          ) : null}

          {progressUpdates.length > 0 ? (
            <div className="workspace__section">
              {progressUpdates.map((update) => (
                <div key={update.id}>
                  {editingId === update.id ? (
                    <SubmissionEditor
                      workspace={workspace}
                      kind="progress_update"
                      submission={update}
                      busy={submitBusy}
                      error={submitError}
                      onCancel={() => {
                        setEditingId(null)
                        setEditorKind(null)
                        setSubmitError(null)
                      }}
                      onSubmit={(values) => void handleUpdate(update.id, values)}
                    />
                  ) : (
                    <ActivitySubmissionCard
                      submission={update}
                      onEdit={(submission) => {
                        setEditingId(submission.id)
                        setEditorKind('progress_update')
                        setSubmitError(null)
                        setNotice(null)
                      }}
                    />
                  )}
                </div>
              ))}
            </div>
          ) : null}
        </section>
      </div>
    </div>
  )
}
