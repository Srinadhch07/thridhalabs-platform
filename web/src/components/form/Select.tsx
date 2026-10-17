/** Select dropdown with shared admin styling. */

import { forwardRef } from 'react'
import type { SelectHTMLAttributes } from 'react'

export interface SelectOption {
  value: string
  label: string
}

export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'onChange'> {
  options: SelectOption[]
  placeholder?: string
  onChange?: (value: string) => void
  invalid?: boolean
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { options, placeholder, onChange, invalid, className = '', value, ...rest },
  ref,
) {
  function handleChange(event: React.ChangeEvent<HTMLSelectElement>): void {
    onChange?.(event.target.value)
  }

  const hasValue = value !== undefined && value !== null && value !== ''
  const placeholderOption = placeholder && !hasValue ? { value: '', label: placeholder } : null

  return (
    <select
      ref={ref}
      className={`select${invalid ? ' select--invalid' : ''}${className ? ` ${className}` : ''}`}
      onChange={handleChange}
      value={value === null || value === undefined ? '' : value}
      {...rest}
    >
      {placeholderOption ? (
        <option value="" disabled>
          {placeholderOption.label}
        </option>
      ) : null}
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  )
})