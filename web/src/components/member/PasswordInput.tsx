/**
 * PasswordInput — password field with an accessible show/hide control.
 *
 * Wraps the shared `TextInput` so form styling and change handling stay
 * consistent with the rest of the portal.
 */

import { useState } from 'react'
import type { InputHTMLAttributes } from 'react'
import { TextInput } from '../form/TextInput'

type PasswordInputProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'onChange' | 'type'
> & {
  onChange?: (value: string) => void
  invalid?: boolean
}

export function PasswordInput({ onChange, invalid, ...rest }: PasswordInputProps) {
  const [visible, setVisible] = useState(false)

  return (
    <div className="member-password">
      <TextInput
        type={visible ? 'text' : 'password'}
        onChange={onChange}
        invalid={invalid}
        {...rest}
      />
      <button
        type="button"
        className="member-password__toggle"
        aria-pressed={visible}
        onClick={() => setVisible((value) => !value)}
      >
        {visible ? 'Hide' : 'Show'}
      </button>
    </div>
  )
}
