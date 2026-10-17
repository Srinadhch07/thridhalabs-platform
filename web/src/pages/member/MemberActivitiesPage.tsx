/**
 * Member activities — browse open programmes/hackathons, self-register and
 * withdraw, and see the projects you have been invited to.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMemberActivities } from '../../features/activities/hooks'
import {
  registerForActivity,
  withdrawFromActivity,
} from '../../features/activities/api'
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

export default function MemberActivitiesPage() {
  usePageMeta({ title: 'Activities — Member portal — Thridha Labs' })

  const { data, loading, error, reload } = useMemberActivities()
  useMemberSessionIssue(error)

  const [busySlug, setBusySlug] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const items = data?.items ?? []

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
    } catch (caught) {
      setActionError(getErrorMessage(caught, 'Could not update your participation.'))
    } finally {
      setBusySlug(null)
    }
  }

  return (
    <div className="member-page">
      <MemberPageHeader
        title="Activities"
        description="Programmes, hackathons and the projects you have been invited to."
      />

      {actionError ? (
        <p className="form-field__error form-field__error--form" role="alert">
          {actionError}
        </p>
      ) : null}

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
                    <p className="member-activity-card__role">Role: {activity.participation_role}</p>
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
    </div>
  )
}
