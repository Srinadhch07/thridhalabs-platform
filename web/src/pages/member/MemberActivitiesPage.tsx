/**
 * Member activities — "My activities": the individual workspaces of the
 * programmes and hackathons you have joined, plus the open activities you can
 * still browse and join.
 *
 * Participation is individual, so a workspace belongs to you alone: your own
 * checklist, your own deliverable and your own progress updates.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMemberActivities } from '../../features/activities/hooks'
import {
  registerForActivity,
  withdrawFromActivity,
} from '../../features/activities/api'
import { useMyActivityWorkspaces } from '../../features/activityWorkspaces/hooks'
import {
  ACTIVITY_TYPE_LABELS,
  PRESENTATION_LABELS,
  PARTICIPATION_STATUS_LABELS,
  formatSchedule,
  isOpenRegistration,
} from '../../features/activities/labels'
import { useMemberSessionIssue } from '../../lib/hooks/useMemberSession'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { usePageMeta } from '../../lib/utils/seo'
import { MemberPageHeader } from '../../components/member/MemberPageHeader'
import { MemberEmptyState } from '../../components/member/MemberEmptyState'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import type { MemberActivity } from '../../types/activity'
import type { ActivityWorkspace } from '../../types/activitySubmission'

function WorkspaceCard({ workspace }: { workspace: ActivityWorkspace }) {
  const typeLabel =
    ACTIVITY_TYPE_LABELS[workspace.activity_type as 'programme' | 'hackathon'] ??
    workspace.activity_type

  return (
    <li className="member-activity-card">
      <div className="member-activity-card__main">
        <div className="member-activity-card__meta">
          <span className="chip">{typeLabel}</span>
          <span className={`chip chip--activity chip--activity-${workspace.presentation_status}`}>
            {PRESENTATION_LABELS[workspace.presentation_status]}
          </span>
          {workspace.deliverable ? (
            <span className="chip chip--muted">Deliverable submitted</span>
          ) : (
            <span className="chip chip--warn">Deliverable pending</span>
          )}
        </div>
        <h3 className="member-activity-card__title">{workspace.title}</h3>
        {workspace.summary ? (
          <p className="member-activity-card__desc">{workspace.summary}</p>
        ) : null}
        {formatSchedule(workspace.start_date, workspace.end_date) ? (
          <p className="member-activity-card__schedule">
            {formatSchedule(workspace.start_date, workspace.end_date)}
          </p>
        ) : null}
        <div className="workspace__progress">
          <div
            className="workspace__progress-track"
            role="progressbar"
            aria-valuenow={workspace.progress_percent}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Task completion for ${workspace.title}`}
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
      </div>
      <div className="member-activity-card__actions">
        <Link className="btn btn--primary btn--sm" to={`/member/activities/${workspace.slug}`}>
          Open workspace
        </Link>
      </div>
    </li>
  )
}

export default function MemberActivitiesPage() {
  usePageMeta({ title: 'My activities — Member portal — Thridha Labs' })

  const { data, loading, error, reload } = useMemberActivities()
  const workspacesState = useMyActivityWorkspaces()
  useMemberSessionIssue(error ?? workspacesState.error)

  const [busySlug, setBusySlug] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const items = data?.items ?? []
  const workspaces = workspacesState.data?.items ?? []

  async function run(activity: MemberActivity, action: 'register' | 'withdraw'): Promise<void> {
    setBusySlug(activity.slug)
    setActionError(null)
    try {
      if (action === 'register') {
        await registerForActivity(activity.slug)
      } else {
        await withdrawFromActivity(activity.slug)
      }
      await reload()
      workspacesState.reload()
    } catch (caught) {
      setActionError(getErrorMessage(caught, 'Could not update your participation.'))
    } finally {
      setBusySlug(null)
    }
  }

  return (
    <div className="member-page">
      <MemberPageHeader
        title="My activities"
        description="Your programme and hackathon workspaces, and the open activities you can still join."
      />

      {actionError ? (
        <p className="form-field__error form-field__error--form" role="alert">
          {actionError}
        </p>
      ) : null}

      <section className="member-stack">
        <h2 className="workspace__section-title">Your workspaces</h2>

        {workspacesState.loading ? <ContentSkeleton rows={2} /> : null}
        {workspacesState.error && !workspacesState.loading ? (
          <ErrorState error={workspacesState.error} onRetry={workspacesState.reload} />
        ) : null}
        {!workspacesState.loading && !workspacesState.error && workspaces.length === 0 ? (
          <MemberEmptyState
            title="No workspaces yet"
            description="Join a programme or hackathon below and your personal workspace will appear here."
          />
        ) : null}

        {workspaces.length > 0 ? (
          <ul className="member-activity-list">
            {workspaces.map((workspace) => (
              <WorkspaceCard key={workspace.activity_id} workspace={workspace} />
            ))}
          </ul>
        ) : null}
      </section>

      <section className="member-stack">
        <h2 className="workspace__section-title">Browse programmes & hackathons</h2>

        {loading ? <ContentSkeleton rows={4} /> : null}
        {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}
        {!loading && !error && items.length === 0 ? (
          <MemberEmptyState
            title="No activities yet"
            description="When open programmes, hackathons or invitations arrive, they will appear here."
          />
        ) : null}

        {items.length > 0 ? (
          <ul className="member-activity-list">
            {items.map((activity) => {
              const busy = busySlug === activity.slug
              const open = isOpenRegistration(activity.activity_type)
              return (
                <li key={activity.slug} className="member-activity-card">
                  <div className="member-activity-card__main">
                    <div className="member-activity-card__meta">
                      <span className="chip">{ACTIVITY_TYPE_LABELS[activity.activity_type]}</span>
                      <span className={`chip chip--activity chip--activity-${activity.presentation_status}`}>
                        {PRESENTATION_LABELS[activity.presentation_status]}
                      </span>
                      {activity.participation_status ? (
                        <span className={`chip chip--part chip--part-${activity.participation_status}`}>
                          {PARTICIPATION_STATUS_LABELS[activity.participation_status]}
                        </span>
                      ) : null}
                    </div>
                    <h3 className="member-activity-card__title">{activity.title}</h3>
                    {activity.summary ? (
                      <p className="member-activity-card__desc">{activity.summary}</p>
                    ) : null}
                    {formatSchedule(activity.start_date, activity.end_date) ? (
                      <p className="member-activity-card__schedule">
                        {formatSchedule(activity.start_date, activity.end_date)}
                      </p>
                    ) : null}
                    {activity.participation_role ? (
                      <p className="member-activity-card__role">
                        Role: {activity.participation_role}
                      </p>
                    ) : null}
                  </div>
                  <div className="member-activity-card__actions">
                    <Link className="btn btn--ghost btn--sm" to={`/activities/${activity.slug}`}>
                      Details
                    </Link>
                    {open && activity.can_register ? (
                      <button
                        type="button"
                        className="btn btn--primary btn--sm"
                        disabled={busy}
                        onClick={() => void run(activity, 'register')}
                      >
                        {busy ? 'Joining…' : 'Join'}
                      </button>
                    ) : null}
                    {activity.can_withdraw ? (
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        disabled={busy}
                        onClick={() => void run(activity, 'withdraw')}
                      >
                        {busy ? 'Withdrawing…' : 'Withdraw'}
                      </button>
                    ) : null}
                  </div>
                </li>
              )
            })}
          </ul>
        ) : null}
      </section>
    </div>
  )
}
