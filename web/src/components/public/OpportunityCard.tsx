/**
 * OpportunityCard — one open role on the public careers page.
 *
 * Cards are not links; each role leads with an "Apply by email" link built
 * from the resolved application email and the careers application template.
 * When no application email is configured the card shows a muted note instead
 * of a broken link — the frontend never fabricates an address.
 */

import type { PublicOpportunity } from '../../types/careers'
import { TechChips } from './TechChips'
import { OPPORTUNITY_TYPE_LABELS, WORK_MODE_LABELS } from './labels'

function mailtoHref(opportunity: PublicOpportunity, template: string | null): string | null {
  if (!opportunity.application_email) return null
  const params = new URLSearchParams()
  params.set('subject', `Application — ${opportunity.title}`)
  if (template?.trim()) params.set('body', template.trim())
  return `mailto:${opportunity.application_email}?${params.toString()}`
}

export interface OpportunityCardProps {
  opportunity: PublicOpportunity
  applicationTemplate: string | null
}

export function OpportunityCard({ opportunity, applicationTemplate }: OpportunityCardProps) {
  const typeLabel =
    opportunity.type === 'other' && opportunity.custom_type
      ? opportunity.custom_type
      : OPPORTUNITY_TYPE_LABELS[opportunity.type]
  const href = mailtoHref(opportunity, applicationTemplate)

  return (
    <article className="opportunity-card">
      <div className="opportunity-card__body">
        <div className="project-card__meta">
          <span className="project-card__type">{typeLabel.toUpperCase()}</span>
          {opportunity.work_mode ? (
            <span>· {WORK_MODE_LABELS[opportunity.work_mode]}</span>
          ) : null}
        </div>
        <h3>{opportunity.title}</h3>
        <p className="project-card__desc">{opportunity.description}</p>
        <TechChips items={opportunity.skills.slice(0, 6)} />
      </div>
      <div className="opportunity-card__actions">
        {href ? (
          <a className="btn" href={href}>
            Apply by email
          </a>
        ) : (
          <p className="form-field__hint">Applications are currently closed for this role.</p>
        )}
      </div>
    </article>
  )
}