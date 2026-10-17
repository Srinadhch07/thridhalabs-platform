/** Shared type labels used across project cards and detail pages. */

import type { ProjectType } from '../../types/content'
import type { OpportunityType, WorkMode } from '../../types/careers'

export const PROJECT_TYPE_LABELS: Record<ProjectType, string> = {
  'client-work': 'Client work',
  product: 'Product',
  experiment: 'Experiment',
  'member-contribution': 'Member contribution',
}

/** Short uppercase HUD label for kernels (e.g. "CLIENT WORK"). */
export const PROJECT_TYPE_SHORT: Record<ProjectType, string> = {
  'client-work': 'CLIENT WORK',
  product: 'PRODUCT',
  experiment: 'EXPERIMENT',
  'member-contribution': 'MEMBER CONTRIBUTION',
}

export const OPPORTUNITY_TYPE_LABELS: Record<OpportunityType, string> = {
  'lab-member': 'Lab Member',
  internship: 'Internship',
  'full-time': 'Full-time',
  'part-time': 'Part-time',
  contract: 'Contract',
  other: 'Other',
}

export const WORK_MODE_LABELS: Record<WorkMode, string> = {
  remote: 'Remote',
  'on-site': 'On-site',
  hybrid: 'Hybrid',
  flexible: 'Flexible',
}

export function initialsOf(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? '')
    .join('')
    .padEnd(1, '·')
}