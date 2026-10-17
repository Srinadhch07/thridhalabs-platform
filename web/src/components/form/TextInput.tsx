/** Text input with shared admin styling. */

import { forwardRef } from 'react'
import type { ChangeEvent, InputHTMLAttributes } from 'react'

export interface TextInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  onChange?: (value: string) => void
  invalid?: boolean
}

export const TextInput = forwardRef<HTMLInputElement, TextInputProps>(function TextInput(
  { onChange, invalid, className = '', ...rest },
  ref,
) {
  function handleChange(event: ChangeEvent<HTMLInputElement>): void {
    onChange?.(event.target.value)
  }

  return (
    <input
      ref={ref}
      className={`text-input${invalid ? ' text-input--invalid' : ''}${className ? ` ${className}` : ''}`}
      onChange={handleChange}
      {...rest}
    />
  )
})