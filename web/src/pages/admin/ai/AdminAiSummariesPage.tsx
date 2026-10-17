import { useState, useCallback, useEffect } from 'react'
import { useSummaryGenerator } from '../../../features/ai/hooks/useSummaryGenerator'
import { useAiSummary, useAiSummaryActions } from '../../../features/ai/hooks/useAi'
import { SaveButton } from '../../../components/form/SaveButton'
import { Textarea } from '../../../components/form/Textarea'
import { FormField } from '../../../components/form/FormField'
import { ContentSkeleton } from '../../../components/ui/ContentSkeleton'
import { ErrorState } from '../../../components/ui/ErrorState'
import { ConfirmDialog } from '../../../components/form/ConfirmDialog'

export default function AdminAiSummariesPage() {
  const {
    sourcesLoading,
    projects,
    currentProject,
    members,
    activityId,
    setActivityId,
    memberId,
    setMemberId,
    canGenerate,
    generating,
    error: genError,
    generated,
    handleGenerate,
  } = useSummaryGenerator()

  const summaryId = generated?.id
  const { data: summary, loading: summaryLoading, error: summaryError, reload: reloadSummary } = useAiSummary(summaryId)

  // Prefer the freshly generated summary until the matching fetch resolves; a
  // previous target's summary must never shadow the one just generated.
  const matchedSummary = summary && summary.id === summaryId ? summary : null
  const activeSummary = matchedSummary ?? generated
  const {
    saveDraft,
    publish,
    unpublish,
    publishing,
    unpublishing,
    saving,
    error: actionError,
  } = useAiSummaryActions(summaryId)

  const [draft, setDraft] = useState('')
  const [publishOpen, setPublishOpen] = useState(false)
  const [unpublishOpen, setUnpublishOpen] = useState(false)

  useEffect(() => {
    if (activeSummary?.draft_content) {
      setDraft(activeSummary.draft_content)
    } else if (activeSummary?.published_content) {
      setDraft(activeSummary.published_content)
    } else {
      setDraft('')
    }
  }, [activeSummary])

  const handleSaveDraft = useCallback(async () => {
    if (!summaryId) return
    try {
      await saveDraft(draft)
      await reloadSummary()
    } catch {
      // Surfaced via `actionError`.
    }
  }, [summaryId, draft, saveDraft, reloadSummary])

  const confirmPublish = useCallback(async () => {
    if (!summaryId) return
    try {
      await publish()
      setPublishOpen(false)
      await reloadSummary()
    } catch {
      // Surfaced via `actionError`; keep the dialog open so the reason is visible.
    }
  }, [summaryId, publish, reloadSummary])

  const confirmUnpublish = useCallback(async () => {
    if (!summaryId) return
    try {
      await unpublish()
      setUnpublishOpen(false)
      await reloadSummary()
    } catch {
      // Surfaced via `actionError`.
    }
  }, [summaryId, unpublish, reloadSummary])

  const pageError = genError || actionError || summaryError

  return (
    <div className="admin-page">
      <header className="admin-page__header">
        <div className="admin-page__header-main">
          <h1 className="admin-page__title">AI Summaries</h1>
          <p className="admin-page__desc">
            Generate and manage contribution summaries from approved reports. Publish only after review.
          </p>
        </div>
      </header>

      {sourcesLoading ? <ContentSkeleton rows={2} /> : null}
      {pageError ? <ErrorState error={pageError} /> : null}

      <div className="member-stack">
        <div className="member-card">
          <h3 className="member-card__title">Select source</h3>
          <div className="form-row">
            <FormField id="project-select" label="Project (Activity)">
              <select
                id="project-select"
                className="select"
                value={activityId}
                onChange={(e) => setActivityId(e.target.value)}
              >
                <option value="">Select project</option>
                {projects.map((p) => (
                  <option key={p.activity_id} value={p.activity_id}>
                    {p.title} ({p.approved_count} approved)
                  </option>
                ))}
              </select>
            </FormField>
            <FormField id="member-select" label="Member">
              <select
                id="member-select"
                className="select"
                value={memberId}
                onChange={(e) => setMemberId(e.target.value)}
                disabled={!members.length}
              >
                {members.map((m) => (
                  <option key={m.member_id} value={m.member_id}>
                    {m.member_name} ({m.approved_count} approved)
                  </option>
                ))}
              </select>
            </FormField>
          </div>
          {currentProject && currentProject.approved_count === 0 && (
            <p className="member-card__desc">No eligible approved reports for this selection.</p>
          )}
          <div className="form-actions">
            <button
              type="button"
              className="btn btn--primary"
              onClick={handleGenerate}
              disabled={!canGenerate || generating}
            >
              {generating ? 'Generating...' : 'Generate summary'}
            </button>
          </div>
        </div>

        {activeSummary && (
          <div className="member-card">
            <h3 className="member-card__title">Summary</h3>
            <dl className="form-list">
              <div className="form-list__item">
                <dt>Project</dt>
                <dd>{activeSummary.activity_title}</dd>
              </div>
              <div className="form-list__item">
                <dt>Member</dt>
                <dd>{activeSummary.member_name}</dd>
              </div>
              <div className="form-list__item">
                <dt>State</dt>
                <dd>{activeSummary.state}</dd>
              </div>
              <div className="form-list__item">
                <dt>Sources</dt>
                <dd>{activeSummary.source_report_count}</dd>
              </div>
              {activeSummary.draft_outdated && (
                <div className="form-list__item">
                  <dt>Draft outdated</dt>
                  <dd>Yes</dd>
                </div>
              )}
              {activeSummary.outdated && (
                <div className="form-list__item">
                  <dt>Published outdated</dt>
                  <dd>Yes</dd>
                </div>
              )}
            </dl>

            <FormField id="draft-content" label="Draft content">
              <Textarea
                id="draft-content"
                value={draft}
                onChange={(value) => setDraft(value)}
                rows={8}
              />
            </FormField>

            <div className="form-actions">
              <SaveButton
                busy={saving}
                onClick={handleSaveDraft}
                disabled={saving || !summaryId}
                type="button"
              >
                {saving ? 'Saving...' : 'Save draft'}
              </SaveButton>
              {activeSummary.state === 'published' || activeSummary.published_content ? (
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => setUnpublishOpen(true)}
                  disabled={unpublishing}
                >
                  {unpublishing ? 'Unpublishing...' : 'Unpublish'}
                </button>
              ) : (
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={() => setPublishOpen(true)}
                  disabled={publishing || !activeSummary.draft_content || !activeSummary.draft_reviewed}
                >
                  {publishing ? 'Publishing...' : 'Publish'}
                </button>
              )}
            </div>
            {activeSummary.state === 'draft' && activeSummary.draft_content && !activeSummary.draft_reviewed ? (
              <p className="member-card__desc">
                Save the draft to review it before publishing.
              </p>
            ) : null}
            {summaryLoading && <ContentSkeleton rows={1} />}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={publishOpen}
        title="Publish summary?"
        body="Publishing will move the reviewed draft into the member's official contribution history. This is an explicit action."
        confirmLabel="Publish"
        cancelLabel="Cancel"
        danger={false}
        busy={publishing}
        onConfirm={confirmPublish}
        onCancel={() => setPublishOpen(false)}
      />
      <ConfirmDialog
        open={unpublishOpen}
        title="Unpublish summary?"
        body="Unpublishing will move the published content back to an editable draft. It will no longer appear in the member's contribution history until republished."
        confirmLabel="Unpublish"
        cancelLabel="Cancel"
        danger
        busy={unpublishing}
        onConfirm={confirmUnpublish}
        onCancel={() => setUnpublishOpen(false)}
      />
    </div>
  )
}