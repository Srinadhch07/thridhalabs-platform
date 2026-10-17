/** Save button with busy/disabled states. */

import type { ButtonHTMLAttributes } from 'react'

export interface SaveButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  busy?: boolean
  busyLabel?: string
  children?: React.ReactNode
}

export function SaveButton({ busy, busyLabel = 'Saving…', children = 'Save changes', disabled, ...rest }: SaveButtonProps) {
  return (
    <button type="submit" className="btn btn--primary" disabled={disabled || busy} {...rest}>
      {busy ? (
        <>
          <span className="spinner spinner--sm" aria-hidden="true" />
          {busyLabel}
        </>
      ) : (
        children
      )}
    </button>
  )
}