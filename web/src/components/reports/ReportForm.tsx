/**
 * ReportForm — authoring/editing form shared by the member submit flow and the
 * edit-and-resubmit flow.
 *
 * Enforces the same limits the API enforces: a required description capped at
 * 500 characters and at most 10 http(s) evidence links. Character/link counts
 * are shown live so the limit is visible before the request is made.
 */

import { useState } from 'react'
import { FormField } from '../form/FormField'
import { Textarea } from '../form/Textarea'
import { TextInput } from '../form/TextInput'
import { SaveButton } from '../form/SaveButton'
import { MAX_REPORT_DESCRIPTION_LENGTH, MAX_REPORT_EVIDENCE_LINKS } from '../../types/report'

export interface ReportFormValues {
  description: string
  evidence_links: string[]
}

export interface ReportFormProps {
  idPrefix: string
  submitLabel: string
  descriptionLabel?: string
  busy?: boolean
  error?: string | null
  initial?: ReportFormValues
  onCancel?: () => void
  onSubmit: (values: ReportFormValues) => void
}

function isValidEvidenceUrl(value: string): boolean {
  try {
    const parsed = new URL(value)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
  } catch {
    return false
  }
}

export function ReportForm({
  idPrefix,
  submitLabel,
  descriptionLabel = 'What did you work on?',
  busy = false,
  error = null,
  initial,
  onCancel,
  onSubmit,
}: ReportFormProps) {
  const [description, setDescription] = useState(initial?.description ?? '')
  const [links, setLinks] = useState<string[]>(initial?.evidence_links ?? [''])
  const [validationError, setValidationError] = useState<string | null>(null)

  const overLimit = description.length > MAX_REPORT_DESCRIPTION_LENGTH

  function patchLink(index: number, value: string): void {
    setLinks((prev) => prev.map((link, i) => (i === index ? value : link)))
  }

  function addLink(): void {
    if (links.length >= MAX_REPORT_EVIDENCE_LINKS) return
    setLinks((prev) => [...prev, ''])
  }

  function removeLink(index: number): void {
    setLinks((prev) => (prev.length === 1 ? [''] : prev.filter((_, i) => i !== index)))
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    setValidationError(null)

    const trimmed = description.trim()
    if (!trimmed) {
      setValidationError('A short description is required.')
      return
    }
    if (trimmed.length > MAX_REPORT_DESCRIPTION_LENGTH) {
      setValidationError(`Descriptions must be at most ${MAX_REPORT_DESCRIPTION_LENGTH} characters.`)
      return
    }

    const evidence = links.map((link) => link.trim()).filter(Boolean)
    if (evidence.length > MAX_REPORT_EVIDENCE_LINKS) {
      setValidationError(`You can attach at most ${MAX_REPORT_EVIDENCE_LINKS} evidence links.`)
      return
    }
    const invalid = evidence.find((link) => !isValidEvidenceUrl(link))
    if (invalid) {
      setValidationError('Evidence links must be full http:// or https:// URLs.')
      return
    }

    onSubmit({ description: trimmed, evidence_links: evidence })
  }

  const fieldError =
    validationError && validationError.includes('description') ? validationError : null
  const shownError = fieldError ? null : (validationError ?? error)

  return (
    <form onSubmit={handleSubmit} noValidate>
      <FormField
        id={`${idPrefix}-description`}
        label={descriptionLabel}
        required
        hint={`${description.length} / ${MAX_REPORT_DESCRIPTION_LENGTH}`}
        error={fieldError}
      >
        <Textarea
          id={`${idPrefix}-description`}
          rows={5}
          value={description}
          invalid={overLimit}
          onChange={(value) => {
            setDescription(value)
            setValidationError(null)
          }}
          placeholder="A short update on your progress…"
        />
      </FormField>

      <FormField
        id={`${idPrefix}-links`}
        label="Evidence links"
        hint={`${links.filter((link) => link.trim()).length} / ${MAX_REPORT_EVIDENCE_LINKS} · optional`}
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
          {links.length < MAX_REPORT_EVIDENCE_LINKS ? (
            <button type="button" className="btn btn--ghost btn--sm" onClick={addLink}>
              Add link
            </button>
          ) : null}
        </div>
      </FormField>

      {shownError ? (
        <p className="form-field__error form-field__error--form" role="alert">
          {shownError}
        </p>
      ) : null}

      <div className="report-form__actions">
        <SaveButton busy={busy} busyLabel="Saving…" disabled={overLimit}>
          {submitLabel}
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
