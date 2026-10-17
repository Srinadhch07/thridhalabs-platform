/** Color input with native picker + hex text field and recoverable editing.
 *
 * The parent keeps the last valid value. While typing, an invalid (or empty)
 * draft is held locally so the preview never breaks and the field stays
 * editable; only a #rrggbb value is emitted via `onChange`. */
import { useEffect, useState } from 'react'
import type { ChangeEvent } from 'react'

export interface ColorInputProps {
  id: string
  label: string
  value: string
  disabled?: boolean
  onChange?: (value: string) => void
  className?: string
}

const HEX_RE = /^#[0-9a-f]{6}$/i

export function ColorInput({ id, label, value, disabled, onChange, className = '' }: ColorInputProps) {
  const [draft, setDraft] = useState(value)

  useEffect(() => {
    setDraft(value)
  }, [value])

  const valid = HEX_RE.test(draft.trim())
  const invalid = draft.trim() !== '' && !valid

  function handlePicker(event: ChangeEvent<HTMLInputElement>): void {
    const next = event.target.value.toLowerCase()
    setDraft(next)
    onChange?.(next)
  }

  function handleText(event: ChangeEvent<HTMLInputElement>): void {
    const next = event.target.value
    setDraft(next)
    if (HEX_RE.test(next.trim())) {
      onChange?.(next.trim().toLowerCase())
    }
  }

  return (
    <div className={`color-field${className ? ` ${className}` : ''}`}>
      <div className={`color-input${invalid ? ' color-input--invalid' : ''}`}>
        <input
          id={id}
          type="color"
          value={valid ? draft : '#000000'}
          disabled={disabled}
          onChange={handlePicker}
          className="color-input__swatch"
          aria-label={label}
        />
        <label className="visually-hidden" htmlFor={`${id}-hex`}>
          {`${label} — hex value`}
        </label>
        <input
          id={`${id}-hex`}
          type="text"
          value={draft}
          disabled={disabled}
          onChange={handleText}
          spellCheck={false}
          autoComplete="off"
          inputMode="text"
          className={`color-input__hex mono${invalid ? ' color-input__hex--invalid' : ''}`}
          aria-label={`${label} — hex value`}
          aria-invalid={invalid || undefined}
          aria-describedby={invalid ? `${id}-error` : undefined}
        />
      </div>
      {invalid ? (
        <p id={`${id}-error`} className="color-input__error" role="alert">
          Enter a #rrggbb hex value
        </p>
      ) : null}
    </div>
  )
}