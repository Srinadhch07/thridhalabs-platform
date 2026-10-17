/** Checkbox with shared admin styling. */

import type { ChangeEvent } from 'react'

export interface CheckboxProps {
  id: string
  label: string
  checked: boolean
  description?: string
  disabled?: boolean
  onChange?: (checked: boolean) => void
  className?: string
}

export function Checkbox({ id, label, description, checked, disabled, onChange, className = '' }: CheckboxProps) {
  function handleChange(event: ChangeEvent<HTMLInputElement>): void {
    onChange?.(event.target.checked)
  }

  return (
    <label className={`checkbox${className ? ` ${className}` : ''}`}>
      <input
        id={id}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={handleChange}
        className="checkbox__input"
      />
      <span className="checkbox__control" aria-hidden="true" />
      <span className="checkbox__text">
        <span className="checkbox__label">{label}</span>
        {description ? <span className="checkbox__description">{description}</span> : null}
      </span>
    </label>
  )
}