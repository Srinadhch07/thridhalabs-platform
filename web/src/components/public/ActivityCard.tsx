/**
 * ActivityCard — one entry in an activity grid or the homepage carousel.
 * The whole card links to the activity detail page. The presentation label is
 * derived server-side from the lifecycle + dates.
 */

import { Link } from 'react-router-dom'
import type { PublicActivity, MemberActivity } from '../../types/activity'
import { MediaTile } from './MediaTile'
import {
  ACTIVITY_TYPE_SHORT,
  PRESENTATION_LABELS,
  formatSchedule,
} from '../../features/activities/labels'

type ActivityCardModel = Pick<
  PublicActivity,
  | 'slug'
  | 'title'
  | 'summary'
  | 'activity_type'
  | 'presentation_status'
  | 'banner_media_id'
  | 'start_date'
  | 'end_date'
  | 'featured'
>

export interface ActivityCardProps {
  activity: ActivityCardModel | MemberActivity
  /** Compact variant used inside the homepage carousel. */
  compact?: boolean
}

export function ActivityCard({ activity, compact = false }: ActivityCardProps) {
  const label = PRESENTATION_LABELS[activity.presentation_status]
  const schedule = formatSchedule(activity.start_date, activity.end_date)
  return (
    <Link
      className={`activity-card${compact ? ' activity-card--compact' : ''}`}
      to={`/activities/${activity.slug}`}
      aria-label={`View activity: ${activity.title}`}
    >
      <div className="activity-card__media">
        <MediaTile
          label={activity.title}
          mediaId={activity.banner_media_id}
          large={!compact}
          hideLabel
          natural
        />
      </div>
      <div className="activity-card__body">
        <div className="activity-card__meta">
          <span className="activity-card__type">{ACTIVITY_TYPE_SHORT[activity.activity_type]}</span>
          <span className={`chip chip--activity chip--activity-${activity.presentation_status}`}>
            {label}
          </span>
          {schedule ? <span className="activity-card__schedule">{schedule}</span> : null}
        </div>
        <h3 className="activity-card__title">{activity.title}</h3>
        {activity.summary ? <p className="activity-card__desc">{activity.summary}</p> : null}
        <span className="activity-card__more">
          View activity <span className="arrow" aria-hidden="true">→</span>
        </span>
      </div>
    </Link>
  )
}
