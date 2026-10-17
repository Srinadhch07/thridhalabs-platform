/**
 * Member "My Projects" — every project the member is a confirmed participant
 * of, with a roll-up of their progress-report state for each one, plus a link
 * into the per-project report history and the official contribution history.
 */

import { Link } from 'react-router-dom'
import { useMemberProjects } from '../../features/reports/hooks'
import { useMemberSessionIssue } from '../../lib/hooks/useMemberSession'
import { usePageMeta } from '../../lib/utils/seo'
import { PRESENTATION_LABELS } from '../../features/activities/labels'
import { MemberPageHeader } from '../../components/member/MemberPageHeader'
import { MemberEmptyState } from '../../components/member/MemberEmptyState'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import type { MemberProjectSummary } from '../../types/report'

function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function scheduleLine(project: MemberProjectSummary): string {
  const { start_date: start, end_date: end } = project
  if (start && end) return `${start} → ${end}`
  if (start) return `From ${start}`
  if (end) return `Until ${end}`
  return ''
}

function RollUp({ project }: { project: MemberProjectSummary }) {
  return (
    <>
      <span className="chip chip--muted">
        {project.report_count} report{project.report_count === 1 ? '' : 's'}
      </span>
      {project.pending_count > 0 ? (
        <span className="chip chip--admin">
          {project.pending_count} awaiting review
        </span>
      ) : null}
      {project.changes_requested_count > 0 ? (
        <span className="chip chip--warn">
          {project.changes_requested_count} changes requested
        </span>
      ) : null}
      {project.approved_count > 0 ? (
        <span className="chip chip--ok">{project.approved_count} approved</span>
      ) : null}
    </>
  )
}

export default function MemberProjectsPage() {
  usePageMeta({ title: 'My Projects — Member portal — Thridha Labs' })

  const { data, loading, error, reload } = useMemberProjects()
  useMemberSessionIssue(error)

  const items = data?.items ?? []

  return (
    <div className="member-page">
      <MemberPageHeader
        title="My Projects"
        description="The projects you contribute to, with your progress-report status for each."
        actions={
          <Link className="btn btn--ghost" to="/member/contributions">
            Contribution history
          </Link>
        }
      />

      {loading ? <ContentSkeleton rows={4} /> : null}
      {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}

      {!loading && !error && items.length === 0 ? (
        <MemberEmptyState
          title="No projects yet"
          description="Once you are confirmed as a participant on a project, it will appear here."
        />
      ) : null}

      {items.length > 0 ? (
        <ul className="member-activity-list">
          {items.map((project) => (
            <li key={project.activity_id} className="member-activity-card">
              <div className="member-activity-card__main">
                <div className="member-activity-card__meta">
                  <span className={`chip chip--activity chip--activity-${project.presentation_status}`}>
                    {PRESENTATION_LABELS[project.presentation_status]}
                  </span>
                  <RollUp project={project} />
                </div>
                <h3 className="member-activity-card__title">{project.title}</h3>
                {scheduleLine(project) ? (
                  <p className="member-activity-card__schedule">{scheduleLine(project)}</p>
                ) : null}
                {project.role ? (
                  <p className="member-activity-card__role">Role: {project.role}</p>
                ) : null}
                <p className="member-activity-card__schedule">
                  {project.last_report_at
                    ? `Last report ${formatDate(project.last_report_at)}`
                    : 'No reports yet'}
                </p>
              </div>
              <div className="member-activity-card__actions">
                <Link
                  className="btn btn--primary btn--sm"
                  to={`/member/projects/${project.activity_id}`}
                >
                  Open reports
                </Link>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
