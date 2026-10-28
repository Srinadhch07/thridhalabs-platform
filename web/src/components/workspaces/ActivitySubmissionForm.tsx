/**
 * ActivitySubmissionForm — authoring form for an activity workspace.
 *
 * Serves both submission kinds:
 * - `progress_update` — a short dated update about work in progress.
 * - `deliverable` — the individual work product, whose required parts are
 *   driven by the activity's `required_deliverables` configuration.
 *
 * The form enforces the same limits the API enforces and shows the counts live
 * so a member never discovers a limit only after a rejected request.
 */

import { useEffect, useState } from 'react'
import { FormField } from '../form/FormField'
import { Textarea } from '../form/Textarea'
import { TextInput } from '../form/TextInput'
import { SaveButton } from '../form/SaveButton'
import {
  MAX_SUBMISSION_ATTACHMENTS,
  MAX_SUBMISSION_DESCRIPTION_LENGTH,
  MAX_SUBMISSION_EVIDENCE_LINKS,
  MAX_SUBMISSION_TITLE_LENGTH,
} from '../../types/activitySubmission'
import type {
  ActivitySubmission,
  ActivitySubmissionKind,
  RequiredDeliverable,
} from '../../types/activitySubmission'

export interface ActivitySubmissionFormValues {
  title: string | null
  description: string
  repository_url: string | null
  demo_url: string | null
  evidence_links: string[]
  attachment_media_ids: string[]
}

export interface ActivitySubmissionFormProps {
  idPrefix: string
  kind: ActivitySubmissionKind
  requiredDeliverables: RequiredDeliverable[]
  busy?: boolean
  error?: string | null
  initial?: ActivitySubmission | null
  submitLabel?: string
  onCancel?: () => void
  onSubmit: (values: ActivitySubmissionFormValues) => void
}

function isValidHttpUrl(value: string): boolean {
  try {
    const parsed = new URL(value)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
  } catch {
    return false
  }
}

export function ActivitySubmissionForm({
  idPrefix,
  kind,
  requiredDeliverables,
  busy = false,
  error = null,
  initial = null,
  submitLabel,
  onCancel,
  onSubmit,
}: ActivitySubmissionFormProps) {
  const [title, setTitle] = useState(initial?.title ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [repositoryUrl, setRepositoryUrl] = useState(initial?.repository_url ?? '')
  const [demoUrl, setDemoUrl] = useState(initial?.demo_url ?? '')
  const [links, setLinks] = useState<string[]>(
    initial?.evidence_links?.length ? initial.evidence_links : [''],
  )
  const [attachments, setAttachments] = useState<string[]>(initial?.attachment_media_ids ?? [])
  const [validationError, setValidationError] = useState<string | null>(null)

  useEffect(() => {
    setTitle(initial?.title ?? '')
    setDescription(initial?.description ?? '')
    setRepositoryUrl(initial?.repository_url ?? '')
    setDemoUrl(initial?.demo_url ?? '')
    setLinks(initial?.evidence_links?.length ? initial.evidence_links : [''])
    setAttachments(initial?.attachment_media_ids ?? [])
    setValidationError(null)
  }, [initial?.id, initial?.version])

  const isDeliverable = kind === 'deliverable'
  const needs = (part: RequiredDeliverable): boolean => requiredDeliverables.includes(part)

  const overTitle = title.length > MAX_SUBMISSION_TITLE_LENGTH
  const overDescription = description.length > MAX_SUBMISSION_DESCRIPTION_LENGTH

  function patchLink(index: number, value: string): void {
    setLinks((prev) => prev.map((link, i) => (i === index ? value : link)))
  }

  function addLink(): void {
    if (links.length >= MAX_SUBMISSION_EVIDENCE_LINKS) return
    setLinks((prev) => [...prev, ''])
  }

  function removeLink(index: number): void {
    setLinks((prev) => (prev.length === 1 ? [''] : prev.filter((_, i) => i !== index)))
  }

  function toggleAttachment(mediaId: string): void {
    setAttachments((prev) => {
      if (prev.includes(mediaId)) return prev.filter((id) => id !== mediaId)
      if (prev.length >= MAX_SUBMISSION_ATTACHMENTS) return prev
      return [...prev, mediaId]
    })
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    setValidationError(null)

    const trimmedTitle = title.trim()
    const trimmedDescription = description.trim()

    if (trimmedTitle.length > MAX_SUBMISSION_TITLE_LENGTH) {
      setValidationError(`Titles must be at most ${MAX_SUBMISSION_TITLE_LENGTH} characters.`)
      return
    }
    if (!trimmedDescription) {
      setValidationError('A description is required.')
      return
    }
    if (trimmedDescription.length > MAX_SUBMISSION_DESCRIPTION_LENGTH) {
      setValidationError(
        `Descriptions must be at most ${MAX_SUBMISSION_DESCRIPTION_LENGTH} characters.`,
      )
      return
    }

    const trimmedRepository = repositoryUrl.trim()
    const trimmedDemo = demoUrl.trim()

    if (trimmedRepository && !isValidHttpUrl(trimmedRepository)) {
      setValidationError('The repository URL must be a full http:// or https:// URL.')
      return
    }
    if (trimmedDemo && !isValidHttpUrl(trimmedDemo)) {
      setValidationError('The demo URL must be a full http:// or https:// URL.')
      return
    }

    const evidence = links.map((link) => link.trim()).filter(Boolean)
    if (evidence.length > MAX_SUBMISSION_EVIDENCE_LINKS) {
      setValidationError(`You can attach at most ${MAX_SUBMISSION_EVIDENCE_LINKS} evidence links.`)
      return
    }
    if (evidence.some((link) => !isValidHttpUrl(link))) {
      setValidationError('Evidence links must be full http:// or https:// URLs.')
      return
    }

    if (isDeliverable) {
      if (needs('description') && !trimmedDescription) {
        setValidationError('This activity requires a description.')
        return
      }
      if (needs('repository_url') && !trimmedRepository) {
        setValidationError('This activity requires a repository URL.')
        return
      }
      if (needs('demo_url') && !trimmedDemo) {
        setValidationError('This activity requires a demo URL.')
        return
      }
      if (needs('evidence_links') && evidence.length === 0) {
        setValidationError('This activity requires at least one evidence link.')
        return
      }
    }

    onSubmit({
      title: trimmedTitle || null,
      description: trimmedDescription,
      repository_url: trimmedRepository || null,
      demo_url: trimmedDemo || null,
      evidence_links: evidence,
      attachment_media_ids: attachments,
    })
  }

  const label = submitLabel ?? (isDeliverable ? 'Submit deliverable' : 'Post update')

  return (
    <form onSubmit={handleSubmit} noValidate>
      {isDeliverable ? (
        <FormField id={`${idPrefix}-title`} label="Title" hint={`${title.length} / ${MAX_SUBMISSION_TITLE_LENGTH}`}>
          <TextInput
            id={`${idPrefix}-title`}
            value={title}
            invalid={overTitle}
            onChange={(value) => {
              setTitle(value)
              setValidationError(null)
            }}
            placeholder="What you built"
          />
        </FormField>
      ) : null}

      <FormField
        id={`${idPrefix}-description`}
        label={isDeliverable ? 'Description' : 'What did you work on?'}
        required
        hint={`${description.length} / ${MAX_SUBMISSION_DESCRIPTION_LENGTH}`}
      >
        <Textarea
          id={`${idPrefix}-description`}
          rows={isDeliverable ? 7 : 5}
          value={description}
          invalid={overDescription}
          onChange={(value) => {
            setDescription(value)
            setValidationError(null)
          }}
          placeholder={isDeliverable ? 'Describe your work…' : 'A short update on your progress…'}
        />
      </FormField>

      {isDeliverable && needs('repository_url') ? (
        <FormField id={`${idPrefix}-repo`} label="Repository URL" required>
          <TextInput
            id={`${idPrefix}-repo`}
            value={repositoryUrl}
            inputMode="url"
            onChange={(value) => {
              setRepositoryUrl(value)
              setValidationError(null)
            }}
            placeholder="https://github.com/…"
          />
        </FormField>
      ) : null}

      {isDeliverable && needs('demo_url') ? (
        <FormField id={`${idPrefix}-demo`} label="Demo URL" required>
          <TextInput
            id={`${idPrefix}-demo`}
            value={demoUrl}
            inputMode="url"
            onChange={(value) => {
              setDemoUrl(value)
              setValidationError(null)
            }}
            placeholder="https://your-demo.example.com"
          />
        </FormField>
      ) : null}

      {isDeliverable && !needs('repository_url') && !needs('demo_url') ? (
        <div className="admin-form__row">
          <FormField id={`${idPrefix}-repo`} label="Repository URL" hint="optional">
            <TextInput
              id={`${idPrefix}-repo`}
              value={repositoryUrl}
              inputMode="url"
              onChange={(value) => {
                setRepositoryUrl(value)
                setValidationError(null)
              }}
              placeholder="https://github.com/…"
            />
          </FormField>
          <FormField id={`${idPrefix}-demo`} label="Demo URL" hint="optional">
            <TextInput
              id={`${idPrefix}-demo`}
              value={demoUrl}
              inputMode="url"
              onChange={(value) => {
                setDemoUrl(value)
                setValidationError(null)
              }}
              placeholder="https://your-demo.example.com"
            />
          </FormField>
        </div>
      ) : null}

      {(isDeliverable || needs('evidence_links')) ? (
        <FormField
          id={`${idPrefix}-links`}
          label="Evidence links"
          required={isDeliverable && needs('evidence_links')}
          hint={`${links.filter((link) => link.trim()).length} / ${MAX_SUBMISSION_EVIDENCE_LINKS}${isDeliverable && !needs('evidence_links') ? ' · optional' : ''}`}
        >
          <div className="report-links">
            {links.map((link, index) => (
              <div className="report-links__row" key={index}>
                <TextInput
                  id={index === 0 ? `${idPrefix}-links` : undefined}
                  aria-label={`Evidence link ${index + 1}`}
                  value={link}
                  onChange={(value) => {
                    patchLink(index, value)
                    setValidationError(null)
                  }}
                  placeholder="https://…"
                  inputMode="url"
                />
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => removeLink(index)}
                  aria-label={`Remove evidence link ${index + 1}`}
                >
                  Remove
                </button>
              </div>
            ))}
            {links.length < MAX_SUBMISSION_EVIDENCE_LINKS ? (
              <button type="button" className="btn btn--ghost btn--sm" onClick={addLink}>
                Add link
              </button>
            ) : null}
          </div>
        </FormField>
      ) : null}

      {attachments.length > 0 ? (
        <FormField
          id={`${idPrefix}-attachments`}
          label="Attachments"
          hint={`${attachments.length} / ${MAX_SUBMISSION_ATTACHMENTS}`}
        >
          <div className="workspace__required">
            {attachments.map((mediaId) => (
              <button
                type="button"
                key={mediaId}
                className="workspace__required-item"
                onClick={() => toggleAttachment(mediaId)}
                title="Remove attachment"
              >
                {mediaId.slice(0, 8)} ×
              </button>
            ))}
          </div>
        </FormField>
      ) : null}

      {error ? (
        <p className="form-field__error form-field__error--form" role="alert">
          {error}
        </p>
      ) : null}
      {validationError ? (
        <p className="form-field__error form-field__error--form" role="alert">
          {validationError}
        </p>
      ) : null}

      <div className="report-form__actions">
        <SaveButton busy={busy} busyLabel="Saving…" disabled={overTitle || overDescription}>
          {label}
        </SaveButton>
        {onCancel ? (
          <button type="button" className="btn btn--ghost" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
        ) : null}
      </div>
    </form>
  )
}
