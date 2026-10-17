/** DecisionHistory — the full recorded reviewer action history for a request. */

import type { CertificationDecision } from '../../types/certification'

function formatDateTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const ACTION_LABELS: Record<string, string> = {
  under_review: 'Marked under review',
  approve: 'Approved',
  request_changes: 'Requested changes',
  reject: 'Rejected',
}

export function DecisionHistory({ decisions }: { decisions: CertificationDecision[] }) {
  if (decisions.length === 0) {
    return <p className="cert-history__empty">No reviewer actions recorded yet.</p>
  }
  return (
    <ol className="cert-history">
      {decisions.map((decision, index) => (
        <li className="cert-history__item" key={index}>
          <p className="cert-history__action">
            {ACTION_LABELS[decision.action] ?? decision.action}{' '}
            <span className="cert-history__meta">
              by {decision.by} ({decision.by_role}) · {formatDateTime(decision.at)}
            </span>
          </p>
          {decision.feedback ? <p className="cert-history__feedback">{decision.feedback}</p> : null}
        </li>
      ))}
    </ol>
  )
}
