/** Activity labels + presentation helpers shared across surfaces. */

import type {
  ActivityPresentationStatus,
  ActivityStatus,
  ActivityType,
  ParticipationStatus,
} from '../../types/activity'

export const ACTIVITY_TYPE_LABELS: Record<ActivityType, string> = {
  project: 'Project',
  programme: 'Programme',
  hackathon: 'Hackathon',
}

/** Short uppercase HUD label (e.g. "PROGRAMME"). */
export const ACTIVITY_TYPE_SHORT: Record<ActivityType, string> = {
  project: 'PROJECT',
  programme: 'PROGRAMME',
  hackathon: 'HACKATHON',
}

export const ACTIVITY_STATUS_LABELS: Record<ActivityStatus, string> = {
  draft: 'Draft',
  published: 'Published',
  cancelled: 'Cancelled',
  archived: 'Archived',
}

/** Public-facing, date-derived label. */
export const PRESENTATION_LABELS: Record<ActivityPresentationStatus, string> = {
  upcoming: 'Coming soon',
  ongoing: 'Ongoing',
  completed: 'Completed',
  cancelled: 'Cancelled',
  archived: 'Archived',
}

export const PARTICIPATION_STATUS_LABELS: Record<ParticipationStatus, string> = {
  invited: 'Invited',
  interested: 'Interested',
  declined: 'Declined',
  confirmed: 'Confirmed',
  withdrawn: 'Withdrawn',
}

/** Activity types that accept open self-registration. */
export function isOpenRegistration(type: ActivityType): boolean {
  return type === 'programme' || type === 'hackathon'
}

/** Human-friendly schedule line (empty string when no dates are set). */
export function formatSchedule(start: string | null, end: string | null): string {
  if (start && end) return `${start} → ${end}`
  if (start) return `From ${start}`
  if (end) return `Until ${end}`
  return ''
}
