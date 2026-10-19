/**
 * Member work editor — create and edit a work: metadata, cover image, tags,
 * external links and the block-based content document. Publication and
 * certification are explicit actions, kept separate from ordinary saves.
 */

import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { useMemberSessionIssue } from '../../lib/hooks/useMemberSession'
import { useBeforeUnload } from '../../lib/hooks/useBeforeUnload'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage, isApiError } from '../../lib/errors/ApiError'
import {
  createMemberWork,
  deleteMemberWork,
  publishMemberWork,
  submitMemberWork,
  unpublishMemberWork,
  updateMemberWork,
  withdrawMemberWork,
} from '../../features/works/api'
import { useMemberWork } from '../../features/works/hooks'
import {
  WORK_STATUS_CHIP,
  WORK_STATUS_LABELS,
  WORK_TEMPLATES,
  WORK_TEMPLATE_DESCRIPTIONS,
  WORK_TEMPLATE_LABELS,
  WORK_VISIBILITY_HINTS,
  WORK_VISIBILITY_LABELS,
} from '../../features/works/status'
import { applyCertification } from '../../features/certifications/api'
import { uploadMemberMedia } from '../../features/media/api'
import { CERTIFICATION_STATUS_LABELS } from '../../features/certifications/status'
import { MemberPageHeader } from '../../components/member/MemberPageHeader'
import { MemberCard } from '../../components/member/MemberCard'
import { ImageUploadField } from '../../components/form/ImageUploadField'
import { BlockEditor } from '../../components/works/BlockEditor'
import { seedTemplate } from '../../components/works/templates'
import { FormField } from '../../components/form/FormField'
import { TextInput } from '../../components/form/TextInput'
import { Textarea } from '../../components/form/Textarea'
import { Select } from '../../components/form/Select'
import { FormActions } from '../../components/form/FormActions'
import { SaveButton } from '../../components/form/SaveButton'
import { ConfirmDialog } from '../../components/form/ConfirmDialog'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { NotFoundState } from '../../components/ui/NotFoundState'
import type { ContentDocument, ExternalLink, WorkTemplate, WorkVisibility } from '../../types/work'

interface EditorForm {
  title: string
  summary: string
  visibility: WorkVisibility
  cover_media_id: string | null
  tags: string
  external_links: ExternalLink[]
  content: ContentDocument
  template: WorkTemplate
}

function parseList(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function createInitialForm(): EditorForm {
  return {
    title: '',
    summary: '',
    visibility: 'private',
    cover_media_id: null,
    tags: '',
    external_links: [],
    content: seedTemplate('blank-canvas'),
    template: 'blank-canvas',
  }
}

export default function WorkEditorPage() {
  const { workId } = useParams<{ workId: string }>()
  const isEdit = Boolean(workId)
  usePageMeta({ title: isEdit ? 'Edit work — Member portal — Thridha Labs' : 'New work — Member portal — Thridha Labs' })

  const navigate = useNavigate()
  const { hash } = useLocation()
  const { data, loading, error, reload } = useMemberWork(workId)
  useMemberSessionIssue(error)

  const [form, setForm] = useState<EditorForm>(createInitialForm)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [actionBusy, setActionBusy] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const hydrated = useRef(false)

  useBeforeUnload(dirty)

  useEffect(() => {
    if (!data || hydrated.current) return
    hydrated.current = true
    setForm({
      title: data.title,
      summary: data.summary,
      visibility: data.visibility,
      cover_media_id: data.cover_media_id,
      tags: data.tags.join(', '),
      external_links: data.external_links.length > 0 ? data.external_links : [],
      content: data.content,
      template: 'blank-canvas',
    })
    setDirty(false)
  }, [data])

  function patch(p: Partial<EditorForm>): void {
    setForm((prev) => ({ ...prev, ...p }))
    setDirty(true)
    setNotice(null)
  }

  function chooseTemplate(template: WorkTemplate): void {
    patch({ template, content: seedTemplate(template) })
  }

  function setLink(index: number, p: Partial<ExternalLink>): void {
    patch({
      external_links: form.external_links.map((link, i) => (i === index ? { ...link, ...p } : link)),
    })
  }

  function addLink(): void {
    patch({ external_links: [...form.external_links, { label: '', url: '' }] })
  }

  function removeLink(index: number): void {
    patch({ external_links: form.external_links.filter((_, i) => i !== index) })
  }

  async function handleSave(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    setSaveError(null)
    setNotice(null)

    const title = form.title.trim()
    if (!title) {
      setSaveError('A title is required.')
      return
    }
    if (!form.summary.trim()) {
      setSaveError('A summary is required.')
      return
    }
    const links = form.external_links.filter((link) => link.label.trim() || link.url.trim())
    if (links.some((link) => !link.label.trim() || !link.url.trim())) {
      setSaveError('Every external link needs both a label and an https URL.')
      return
    }

    setSaving(true)
    try {
      if (isEdit && workId) {
        await updateMemberWork(workId, {
          title,
          summary: form.summary.trim(),
          cover_media_id: form.cover_media_id,
          tags: parseList(form.tags),
          external_links: links,
          content: form.content,
          visibility: form.visibility,
        })
        setNotice('Work saved.')
        setDirty(false)
        hydrated.current = false
        await reload()
      } else {
        const created = await createMemberWork({
          title,
          summary: form.summary.trim(),
          template: form.template,
          cover_media_id: form.cover_media_id,
          tags: parseList(form.tags),
          external_links: links,
          content: form.content,
          visibility: form.visibility,
        })
        setDirty(false)
        navigate(`/member/works/${created.id}/edit`, { replace: true })
      }
    } catch (caught) {
      setSaveError(getErrorMessage(caught, 'Could not save this work.'))
    } finally {
      setSaving(false)
    }
  }

  async function runAction(action: () => Promise<unknown>, message: string): Promise<void> {
    setActionBusy(true)
    setActionError(null)
    try {
      await action()
      setNotice(message)
      setDirty(false)
      hydrated.current = false
      await reload()
    } catch (caught) {
      setActionError(getErrorMessage(caught, 'The action could not be completed.'))
    } finally {
      setActionBusy(false)
    }
  }

  async function handleDelete(): Promise<void> {
    if (!workId) return
    setActionBusy(true)
    setActionError(null)
    try {
      await deleteMemberWork(workId)
      navigate('/member/works', { replace: true })
    } catch (caught) {
      setActionError(getErrorMessage(caught, 'Could not delete this work.'))
      setActionBusy(false)
      setConfirmDelete(false)
    }
  }

  useEffect(() => {
    if (hash !== '#certification') return
    if (!data) return
    const panel = document.getElementById('certification')
    if (panel && typeof panel.scrollIntoView === 'function') {
      panel.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [data, hash])

  if (isEdit && loading) return <ContentSkeleton rows={6} />
  if (isEdit && error) {
    if (isApiError(error) && error.status === 404) return <NotFoundState />
    return <ErrorState error={error} onRetry={reload} />
  }

  const certification = data?.certification
  const status = data?.publication_status

  return (
    <div className="member-page">
      <MemberPageHeader
        eyebrow="Work Showcase"
        title={isEdit ? 'Edit work' : 'New work'}
        description={
          isEdit
            ? 'Update your work, then publish or request a certification review.'
            : 'Give your work a title and summary, then build its content.'
        }
        actions={
          isEdit && workId ? (
            <Link className="btn btn--ghost" to={`/member/works/${workId}/preview`}>
              Preview
            </Link>
          ) : undefined
        }
      />

      {isEdit && data ? (
        <div className="member-stack member-form">
        <MemberCard>
          <div className="work-editor__status">
            <div className="work-editor__status-chips">
              {status ? (
                <span className={`chip ${WORK_STATUS_CHIP[status]}`}>{WORK_STATUS_LABELS[status]}</span>
              ) : null}
              <span className="chip">{WORK_VISIBILITY_LABELS[form.visibility]}</span>
              {certification?.status ? (
                <span className="chip">{CERTIFICATION_STATUS_LABELS[certification.status]}</span>
              ) : null}
            </div>

            <div className="work-editor__status-actions">
              {status === 'published' ? (
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  disabled={actionBusy}
                  onClick={() => workId && void runAction(() => unpublishMemberWork(workId), 'Work unpublished.')}
                >
                  Unpublish
                </button>
              ) : (
                <button
                  type="button"
                  className="btn btn--primary btn--sm"
                  disabled={actionBusy}
                  onClick={() => workId && void runAction(() => publishMemberWork(workId), 'Work published.')}
                >
                  Publish
                </button>
              )}
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                disabled={actionBusy}
                onClick={() => setConfirmDelete(true)}
              >
                Delete
              </button>
            </div>
          </div>

          <div className="work-cert-panel" id="publication-review">
            <p className="work-cert-panel__title">Publication review</p>
            {status === 'pending_review' ||
            status === 'changes_requested' ||
            status === 'rejected' ? (
              <p className="work-cert-panel__state">
                Status: <strong>{status ? WORK_STATUS_LABELS[status] : ''}</strong>
              </p>
            ) : status === 'published' ? (
              <p className="work-cert-panel__state">Approved by the lab.</p>
            ) : (
              <p className="work-cert-panel__state">
                Submit this work for lab review to have it approved and published on your
                showcase. Only the lab can approve a submission.
              </p>
            )}
            {data?.review_feedback ? (
              <p className="work-cert-panel__feedback">
                Reviewer feedback: {data.review_feedback}
              </p>
            ) : null}
            {status === 'pending_review' ? (
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                disabled={actionBusy}
                onClick={() =>
                  workId && void runAction(() => withdrawMemberWork(workId), 'Submission withdrawn.')
                }
              >
                Withdraw submission
              </button>
            ) : status === 'published' ? (
              <p className="work-cert-panel__hint">
                {data?.featured_on_projects
                  ? 'This work is featured on the official Projects page.'
                  : 'Approved works may be featured on the official Projects page by the lab.'}
              </p>
            ) : (
              <button
                type="button"
                className="btn btn--primary btn--sm"
                disabled={actionBusy}
                onClick={() =>
                  workId && void runAction(() => submitMemberWork(workId), 'Submitted for publication review.')
                }
              >
                {status === 'changes_requested' || status === 'rejected'
                  ? 'Resubmit for Publication Review'
                  : 'Submit for Publication Review'}
              </button>
            )}
          </div>

          <div className="work-cert-panel" id="certification">
            <p className="work-cert-panel__title">Certification</p>
            {certification?.status ? (
              <p className="work-cert-panel__state">
                Status: <strong>{CERTIFICATION_STATUS_LABELS[certification.status]}</strong>
                {certification.changed_since_review ? ' · changed since review' : ''}
              </p>
            ) : (
              <p className="work-cert-panel__state">Not submitted for review.</p>
            )}
            {certification?.feedback ? (
              <p className="work-cert-panel__feedback">
                Reviewer feedback: {certification.feedback}
              </p>
            ) : null}
            {certification?.reviewable ? (
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                disabled={actionBusy}
                onClick={() =>
                  workId &&
                  void runAction(() => applyCertification({ work_id: workId }), 'Submitted for certification review.')
                }
              >
                {certification.status ? 'Request a New Review' : 'Submit for Certification Review'}
              </button>
            ) : status !== 'published' ? (
              <p className="work-cert-panel__hint">Publish this work to submit it for certification review.</p>
            ) : (
              <p className="work-cert-panel__hint">This work already has an active certification request.</p>
            )}
            <p className="work-cert-panel__hint">
              <Link to="/member/certifications">View all certification requests</Link>
            </p>
          </div>
        </MemberCard>
        </div>
      ) : null}

      <form className="member-stack member-form" onSubmit={handleSave} noValidate>
        <MemberCard title="Details">
          <FormField id="work-title" label="Title" required>
            <TextInput
              id="work-title"
              value={form.title}
              maxLength={150}
              onChange={(value) => patch({ title: value })}
              placeholder="A clear, descriptive title"
            />
          </FormField>
          <FormField id="work-summary" label="Summary" hint="Shown in lists and previews" required>
            <Textarea
              id="work-summary"
              rows={3}
              value={form.summary}
              maxLength={2000}
              onChange={(value) => patch({ summary: value })}
              placeholder="One or two sentences describing the work"
            />
          </FormField>
          <FormField
            id="work-visibility"
            label="Visibility"
            hint={WORK_VISIBILITY_HINTS[form.visibility]}
          >
            <Select
              id="work-visibility"
              value={form.visibility}
              options={Object.entries(WORK_VISIBILITY_LABELS).map(([value, label]) => ({ value, label }))}
              onChange={(value) => patch({ visibility: value as WorkVisibility })}
            />
          </FormField>
          <FormField id="work-tags" label="Tags" hint="Comma-separated">
            <TextInput
              id="work-tags"
              value={form.tags}
              onChange={(value) => patch({ tags: value })}
              placeholder="Robotics, Vision, Prototype"
            />
          </FormField>
          {!isEdit ? (
            <FormField id="work-template" label="Starting template" hint={WORK_TEMPLATE_DESCRIPTIONS[form.template]}>
              <Select
                id="work-template"
                value={form.template}
                options={WORK_TEMPLATES.map((template) => ({ value: template, label: WORK_TEMPLATE_LABELS[template] }))}
                onChange={(value) => chooseTemplate(value as WorkTemplate)}
              />
            </FormField>
          ) : null}
        </MemberCard>

        <MemberCard title="Cover image">
          <ImageUploadField
            id="work-cover"
            label="Cover image"
            value={form.cover_media_id}
            onChange={(mediaId) => patch({ cover_media_id: mediaId })}
            upload={uploadMemberMedia}
          />
        </MemberCard>

        <MemberCard title="External links">
          {form.external_links.length === 0 ? (
            <p className="member-card__desc">No links yet.</p>
          ) : null}
          <div className="member-stack">
            {form.external_links.map((link, index) => (
              <div className="work-link-row" key={index}>
                <TextInput
                  id={`work-link-label-${index}`}
                  aria-label={`Link ${index + 1} label`}
                  value={link.label}
                  placeholder="Label"
                  onChange={(value) => setLink(index, { label: value })}
                />
                <TextInput
                  id={`work-link-url-${index}`}
                  aria-label={`Link ${index + 1} URL`}
                  type="url"
                  value={link.url}
                  placeholder="https://…"
                  onChange={(value) => setLink(index, { url: value })}
                />
                <button type="button" className="btn btn--ghost btn--sm" onClick={() => removeLink(index)}>
                  Remove
                </button>
              </div>
            ))}
          </div>
          <button type="button" className="btn btn--ghost btn--sm" onClick={addLink}>
            Add link
          </button>
        </MemberCard>

        <MemberCard title="Content">
          <BlockEditor document={form.content} onChange={(content) => patch({ content })} />
        </MemberCard>

        {saveError ? (
          <p className="form-field__error form-field__error--form" role="alert">
            {saveError}
          </p>
        ) : null}
        {notice ? (
          <p className="admin-form__dirty" role="status">
            {notice}
          </p>
        ) : null}
        {dirty ? (
          <p className="admin-form__dirty" role="status">
            Unsaved changes.
          </p>
        ) : null}
        {actionError ? (
          <p className="form-field__error form-field__error--form" role="alert">
            {actionError}
          </p>
        ) : null}

        <FormActions cancelTo="/member/works">
          <SaveButton busy={saving}>{isEdit ? 'Save changes' : 'Create work'}</SaveButton>
        </FormActions>
      </form>

      <ConfirmDialog
        open={confirmDelete}
        title="Delete this work?"
        body="This work and its content will be permanently removed. This cannot be undone."
        confirmLabel="Delete"
        busy={actionBusy}
        onConfirm={() => void handleDelete()}
        onCancel={() => {
          if (!actionBusy) setConfirmDelete(false)
        }}
      />
    </div>
  )
}
