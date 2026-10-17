/** Presentation labels/chips for work status, visibility and templates. */

import type {
  WorkPublicationStatus,
  WorkReviewAction,
  WorkTemplate,
  WorkVisibility,
} from '../../types/work'

export const WORK_STATUS_LABELS: Record<WorkPublicationStatus, string> = {
  draft: 'Draft',
  pending_review: 'Pending review',
  changes_requested: 'Changes requested',
  rejected: 'Rejected',
  published: 'Published',
  unpublished: 'Unpublished',
}

export const WORK_STATUS_CHIP: Record<WorkPublicationStatus, string> = {
  draft: 'chip--muted',
  pending_review: 'chip--admin',
  changes_requested: 'chip--warn',
  rejected: 'chip--warn',
  published: 'chip--ok',
  unpublished: 'chip--muted',
}

/** Publication-review decisions (admin). */
export const WORK_REVIEW_ACTION_LABELS: Record<WorkReviewAction, string> = {
  approve: 'Approve & publish',
  request_changes: 'Request changes',
  reject: 'Reject',
}

export const WORK_REVIEW_FEEDBACK_ACTIONS: WorkReviewAction[] = [
  'request_changes',
  'reject',
]

export const WORK_VISIBILITY_LABELS: Record<WorkVisibility, string> = {
  private: 'Private',
  members: 'Members',
  public: 'Public',
}

export const WORK_VISIBILITY_CHIP: Record<WorkVisibility, string> = {
  private: 'chip--muted',
  members: 'chip--admin',
  public: 'chip--ok',
}

export const WORK_VISIBILITY_HINTS: Record<WorkVisibility, string> = {
  private: 'Only you can see this work.',
  members: 'Signed-in lab members can see this work.',
  public: 'Anyone can see this work on your public profile.',
}

export const WORK_TEMPLATES: WorkTemplate[] = [
  'blank-canvas',
  'project-showcase',
  'research',
  'creative-portfolio',
]

export const WORK_TEMPLATE_LABELS: Record<WorkTemplate, string> = {
  'blank-canvas': 'Blank canvas',
  'project-showcase': 'Project showcase',
  research: 'Research',
  'creative-portfolio': 'Creative portfolio',
}

export const WORK_TEMPLATE_DESCRIPTIONS: Record<WorkTemplate, string> = {
  'blank-canvas': 'Start from an empty page and add any blocks you like.',
  'project-showcase': 'Overview, highlights and results for a shipped project.',
  research: 'Question, approach, findings and a pull quote.',
  'creative-portfolio': 'Concept, image gallery and process notes.',
}
