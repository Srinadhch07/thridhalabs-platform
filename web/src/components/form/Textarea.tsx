/** Textarea with shared admin styling. */

import { forwardRef } from 'react'
import type { TextareaHTMLAttributes } from 'react'

export interface TextareaProps extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'onChange'> {
  onChange?: (value: string) => void
  invalid?: boolean
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { onChange, invalid, className = '', ...rest },
  ref,
) {
  return (
    <textarea
      ref={ref}
      className={`textarea${invalid ? ' textarea--invalid' : ''}${className ? ` ${className}` : ''}`}
      onChange={(event) => onChange?.(event.target.value)}
      {...rest}
    />
  )
})