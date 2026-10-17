/**
 * Member contribution history — the member's official record of approved
 * progress reports, grouped by project.
 *
 * This is a **private** member-portal view: it is scoped to your own session
 * and is never published to the public portfolio or profile. Only `approved`
 * reports appear here, alongside any explicitly published (Admin-reviewed)
 * AI summaries.
 */

import { Link } from 'react-router-dom'
import { useContributionHistory } from '../../features/reports/hooks'
import { useMemberSessionIssue } from '../../lib/hooks/useMemberSession'
import { usePageMeta } from '../../lib/utils/seo'
import { EvidenceLinks } from '../../components/reports/EvidenceLinks'
import { MemberPageHeader } from '../../components/member/MemberPageHeader'
import { MemberEmptyState } from '../../components/member/MemberEmptyState'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'

function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export default function MemberContributionsPage() {
  usePageMeta({ title: 'Contribution history — Member portal — Thridha Labs' })

  const { data, loading, error, reload } = useContributionHistory()
  useMemberSessionIssue(error)

  const items = data?.items ?? []
  const totalReports = data?.total_reports ?? 0

  return (
    <div className="member-page">
      <MemberPageHeader
        title="Contribution history"
        description="Approved progress reports, grouped by project. This view is private to you."
        actions={
          <Link className="btn btn--ghost" to="/member/projects">
            My projects
          </Link>
        }
      />

      <div className="member-stack">
        <p className="member-card__desc">
          Only reports approved by the lab team count as contributions. These are never published
          automatically — your public showcase is managed separately from Work Showcase.
        </p>

        {loading ? <ContentSkeleton rows={4} /> : null}
        {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}

        {!loading && !error && items.length === 0 ? (
          <MemberEmptyState
            title="No approved reports yet"
            description="Once a progress report you submit is approved, it will show up here."
          />
        ) : null}

        {items.length > 0 ? (
          <>
            <p className="member-card__desc">
              {totalReports} approved report{totalReports === 1 ? '' : 's'} across{' '}
              {items.length} project{items.length === 1 ? '' : 's'}.
            </p>
            <ul className="member-activity-list">
              {items.map((group) => (
                <li key={group.activity_id} className="member-activity-card">
                  <div className="member-activity-card__main">
                    <div className="member-activity-card__meta">
                      <span className="chip chip--ok">
                        {group.report_count} approved
                      </span>
                      {group.role ? <span className="chip chip--muted">{group.role}</span> : null}
                    </div>
                    <h3 className="member-activity-card__title">{group.title}</h3>

                    {group.summaries.map((summary) => (
                      <div key={summary.id} className="report-card report-card--summary">
                        <div className="report-card__head">
                          <span className="chip chip--info">AI-generated · Admin-reviewed</span>
                          <span className="report-card__meta mono">
                            Published {formatDate(summary.published_at)}
                            {summary.model ? ` · ${summary.model}` : ''} ·{' '}
                            {summary.source_report_count} source report
                            {summary.source_report_count === 1 ? '' : 's'}
                          </span>
                        </div>
                        <p className="report-card__desc" style={{ whiteSpace: 'pre-wrap' }}>
                          {summary.content}
                        </p>
                      </div>
                    ))}

                    <ol className="report-list">
                      {group.reports.map((report) => (
                        <li key={report.id} className="report-card">
                          <div className="report-card__head">
                            <span className="report-card__meta mono">
                              Approved {formatDate(report.approved_at)} · submitted{' '}
                              {formatDate(report.submitted_at)}
                            </span>
                          </div>
                          <p className="report-card__desc">{report.description}</p>
                          <EvidenceLinks links={report.evidence_links} />
                        </li>
                      ))}
                    </ol>
                  </div>
                </li>
              ))}
            </ul>
          </>
        ) : null}
      </div>
    </div>
  )
}
