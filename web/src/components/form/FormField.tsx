/**
 * FormField — label + hint + error wrapper shared by every admin input.
 */

import type { ReactNode } from 'react'

interface FormFieldProps {
  id: string
  label: string
  hint?: ReactNode
  error?: string | null
  required?: boolean
  children: ReactNode
  className?: string
}

export function FormField({ id, label, hint, error, required, children, className = '' }: FormFieldProps) {
  return (
    <div className={`form-field${error ? ' form-field--invalid' : ''}${className ? ` ${className}` : ''}`}>
      <div className="form-field__label-row">
        <label className="form-field__label" htmlFor={id}>
          {label}
          {required ? <span className="form-field__required" aria-hidden="true"> *</span> : null}
        </label>
        {hint ? <span className="form-field__hint">{hint}</span> : null}
      </div>
      {children}
      {error ? (
        <p className="form-field__error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}