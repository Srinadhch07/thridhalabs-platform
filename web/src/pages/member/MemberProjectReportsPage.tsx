/**
 * Member project reports — submit a short progress report for one of the
 * projects you are a confirmed participant of, and view/edit/resubmit your own
 * reports for that project.
 *
 * Reports are a private member-portal surface: nothing here is published
 * anywhere public. Only an `approved` report is counted in your contribution
 * history.
 */

import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMemberProjects, useMemberReports } from '../../features/reports/hooks'
import { createMemberReport, updateMemberReport } from '../../features/reports/api'
import { useMemberSessionIssue } from '../../lib/hooks/useMemberSession'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { PRESENTATION_LABELS } from '../../features/activities/labels'
import { ReportForm } from '../../components/reports/ReportForm'
import type { ReportFormValues } from '../../components/reports/ReportForm'
import { ReportStatusChip } from '../../components/reports/ReportStatusChip'
import { EvidenceLinks } from '../../components/reports/EvidenceLinks'
import { ReviewHistory } from '../../components/reports/ReviewHistory'
import { MemberPageHeader } from '../../components/member/MemberPageHeader'
import { MemberEmptyState } from '../../components/member/MemberEmptyState'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { NotFoundState } from '../../components/ui/NotFoundState'
import type { MemberProjectSummary, MemberReport } from '../../types/report'

/** Idempotency key so a retried submit cannot create duplicate reports. */
function newRequestId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `report-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function RollUp({ project }: { project: MemberProjectSummary }) {
  return (
    <div className="member-activity-card__meta">
      <span className={`chip chip--activity chip--activity-${project.presentation_status}`}>
        {PRESENTATION_LABELS[project.presentation_status]}
      </span>
      <span className="chip chip--muted">
        {project.report_count} report{project.report_count === 1 ? '' : 's'}
      </span>
      {project.pending_count > 0 ? (
        <span className="chip chip--admin">{project.pending_count} awaiting review</span>
      ) : null}
      {project.changes_requested_count > 0 ? (
        <span className="chip chip--warn">{project.changes_requested_count} changes requested</span>
      ) : null}
      {project.approved_count > 0 ? (
        <span className="chip chip--ok">{project.approved_count} approved</span>
      ) : null}
    </div>
  )
}

export default function MemberProjectReportsPage() {
  const { activityId } = useParams<{ activityId: string }>()
  usePageMeta({ title: 'Project reports — Member portal — Thridha Labs' })

  const projectsState = useMemberProjects()
  const reportsState = useMemberReports({
    activity_id: activityId ?? '',
    page: 1,
    page_size: 100,
  })
  useMemberSessionIssue(reportsState.error)

  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingBusy, setEditingBusy] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)

  const project = projectsState.data?.items.find((item) => item.activity_id === activityId)
  const reports = reportsState.data?.items ?? []

  async function refresh(): Promise<void> {
    reportsState.reload()
    projectsState.reload()
  }

  async function handleCreate(values: ReportFormValues): Promise<void> {
    if (!activityId) return
    setCreateError(null)
    setNotice(null)
    setCreating(true)
    try {
      await createMemberReport({
        activity_id: activityId,
        description: values.description,
        evidence_links: values.evidence_links,
        client_request_id: newRequestId(),
      })
      setNotice('Report submitted for review.')
      await refresh()
    } catch (caught) {
      setCreateError(getErrorMessage(caught, 'Could not submit your report.'))
    } finally {
      setCreating(false)
    }
  }

  async function handleEdit(reportId: string, values: ReportFormValues): Promise<void> {
    setEditError(null)
    setNotice(null)
    setEditingBusy(true)
    try {
      await updateMemberReport(reportId, {
        description: values.description,
        evidence_links: values.evidence_links,
      })
      setEditingId(null)
      setNotice('Report resubmitted for review.')
      await refresh()
    } catch (caught) {
      setEditError(getErrorMessage(caught, 'Could not update your report.'))
    } finally {
      setEditingBusy(false)
    }
  }

  if (projectsState.loading) return <ContentSkeleton rows={6} />
  if (projectsState.error) {
    return <ErrorState error={projectsState.error} onRetry={projectsState.reload} />
  }
  if (!project) return <NotFoundState title="Project not found" />

  return (
    <div className="member-page">
      <MemberPageHeader
        eyebrow="My Projects"
        title={project.title}
        description={
          project.role
            ? `Your role: ${project.role}. Submit short progress updates as you go.`
            : 'Submit short progress updates as you go.'
        }
        actions={
          <Link className="btn btn--ghost" to="/member/projects">
            ← All projects
          </Link>
        }
      />

      <div className="member-stack">
        <RollUp project={project} />

        {notice ? (
          <p className="form-field__error form-field__error--form" role="status">
            {notice}
          </p>
        ) : null}

        <section className="member-card">
          <div className="member-card__header">
            <div>
              <h2 className="member-card__title">Submit a progress report</h2>
              <p className="member-card__desc">
                Keep it short — what changed, what is next, and any links that prove it.
              </p>
            </div>
          </div>
          <ReportForm
            idPrefix="report-new"
            submitLabel="Submit report"
            busy={creating}
            error={createError}
            onSubmit={(values) => void handleCreate(values)}
          />
        </section>

        <section className="member-card">
          <div className="member-card__header">
            <div>
              <h2 className="member-card__title">Your reports</h2>
              <p className="member-card__desc">
                Pending and changes-requested reports can be edited and resubmitted. Approved
                reports are final.
              </p>
            </div>
          </div>

          {reportsState.loading ? <ContentSkeleton rows={3} /> : null}
          {reportsState.error && !reportsState.loading ? (
            <ErrorState error={reportsState.error} onRetry={reportsState.reload} />
          ) : null}

          {!reportsState.loading && !reportsState.error && reports.length === 0 ? (
            <MemberEmptyState
              title="No reports yet"
              description="Your submitted progress reports for this project will appear here."
            />
          ) : null}

          {reports.length > 0 ? (
            <ul className="report-list">
              {reports.map((report) => (
                <ReportListItem
                  key={report.id}
                  report={report}
                  editing={editingId === report.id}
                  editBusy={editingBusy && editingId === report.id}
                  editError={editingId === report.id ? editError : null}
                  onEdit={() => {
                    setEditingId(report.id)
                    setEditError(null)
                    setNotice(null)
                  }}
                  onCancelEdit={() => setEditingId(null)}
                  onSubmitEdit={(values) => void handleEdit(report.id, values)}
                />
              ))}
            </ul>
          ) : null}
        </section>
      </div>
    </div>
  )
}

interface ReportListItemProps {
  report: MemberReport
  editing: boolean
  editBusy: boolean
  editError: string | null
  onEdit: () => void
  onCancelEdit: () => void
  onSubmitEdit: (values: ReportFormValues) => void
}

function ReportListItem({
  report,
  editing,
  editBusy,
  editError,
  onEdit,
  onCancelEdit,
  onSubmitEdit,
}: ReportListItemProps) {
  return (
    <li className="report-card">
      <div className="report-card__head">
        <ReportStatusChip status={report.status} />
        <span className="report-card__meta mono">
          v{report.version} · submitted {formatDate(report.submitted_at)}
          {report.reviewed_at ? ` · reviewed ${formatDate(report.reviewed_at)}` : ''}
        </span>
      </div>

      {report.review_feedback && report.status === 'changes_requested' ? (
        <p className="report-card__feedback">
          Reviewer feedback: {report.review_feedback}
        </p>
      ) : null}

      {editing ? (
        <ReportForm
          idPrefix={`report-edit-${report.id}`}
          submitLabel="Resubmit for review"
          descriptionLabel="What changed in this update?"
          busy={editBusy}
          error={editError}
          initial={{ description: report.description, evidence_links: report.evidence_links }}
          onCancel={onCancelEdit}
          onSubmit={onSubmitEdit}
        />
      ) : (
        <>
          <p className="report-card__desc">{report.description}</p>
          <EvidenceLinks links={report.evidence_links} />
          <ReviewHistory history={report.review_history} />
          {report.editable ? (
            <div className="report-card__actions">
              <button type="button" className="btn btn--ghost btn--sm" onClick={onEdit}>
                Edit &amp; resubmit
              </button>
            </div>
          ) : null}
        </>
      )}
    </li>
  )
}
