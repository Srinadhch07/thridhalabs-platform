/**
 * Member onboarding — completes setup from an emailed single-use link.
 *
 * The link is `…/member/setup?token=…`; the token is sent once, consumed once
 * and never stored in the client. On success the member is directed to sign in
 * (setting the password does not itself start a session).
 */

import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { memberSetup } from '../../features/members/api'
import { isApiError, getErrorMessage } from '../../lib/errors/ApiError'
import { usePageMeta } from '../../lib/utils/seo'
import { FormField } from '../../components/form/FormField'
import { PasswordInput } from '../../components/member/PasswordInput'
import { SaveButton } from '../../components/form/SaveButton'

export default function MemberSetupPage() {
  usePageMeta({ title: 'Complete your setup — Thridha Labs' })

  const [params] = useSearchParams()
  const token = params.get('token')?.trim() ?? ''

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    if (password.length < 10) {
      setFieldError('Choose a password of at least 10 characters.')
      return
    }
    if (password !== confirm) {
      setFieldError('The passwords do not match.')
      return
    }

    setSubmitting(true)
    setFormError(null)
    setFieldError(null)
    try {
      await memberSetup({ token, password })
      setDone(true)
      setPassword('')
      setConfirm('')
    } catch (caught) {
      if (isApiError(caught) && caught.status === 400) {
        const code = caught.code
        if (code === 'INVALID_ONBOARDING_TOKEN') {
          setFormError('This setup link is no longer valid. Ask the lab team for a new one.')
        } else if (code === 'ONBOARDING_TOKEN_EXPIRED') {
          setFormError('This setup link has expired. Ask the lab team to resend it.')
        } else if (code === 'WEAK_PASSWORD') {
          setFormError(getErrorMessage(caught, 'Choose a stronger password.'))
        } else {
          setFormError(getErrorMessage(caught, 'Unable to complete setup. Please try again.'))
        }
      } else if (isApiError(caught) && caught.status === 429) {
        setFormError('Too many attempts. Please wait a moment and try again.')
      } else {
        setFormError(getErrorMessage(caught, 'Unable to complete setup. Please try again.'))
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="member-auth">
      <div className="member-auth__panel">
        <div className="member-auth__brand">
          <span className="member-brand__mark" aria-hidden="true">
            TL
          </span>
          <span className="member-brand__text">
            <span className="member-brand__name">Thridha Labs</span>
            <span className="member-brand__area">Member area</span>
          </span>
        </div>

        <div className="member-auth__card">
          <h1 className="member-auth__title">Complete your setup</h1>

          {!token ? (
            <div className="member-auth__stack">
              <p className="member-auth__lead">
                This page expects a setup link with a token. Open the link from your invitation
                email, or ask the lab team to resend it.
              </p>
              <div>
                <Link className="btn btn--ghost" to="/member/login">
                  Back to sign in
                </Link>
              </div>
            </div>
          ) : done ? (
            <div className="member-auth__stack">
              <p className="member-auth__lead">
                Your password is set. You can now sign in to your member portal.
              </p>
              <div>
                <Link className="btn btn--primary" to="/member/login">
                  Go to sign in
                </Link>
              </div>
            </div>
          ) : (
            <>
              <p className="member-auth__lead">Choose a password to activate your account.</p>
              <form className="member-auth__form" onSubmit={handleSubmit} noValidate>
                <FormField
                  id="member-setup-password"
                  label="Password"
                  hint="At least 10 characters"
                  required
                >
                  <PasswordInput
                    id="member-setup-password"
                    autoComplete="new-password"
                    value={password}
                    onChange={setPassword}
                    placeholder="••••••••"
                  />
                </FormField>

                <FormField id="member-setup-confirm" label="Confirm password" required>
                  <PasswordInput
                    id="member-setup-confirm"
                    autoComplete="new-password"
                    value={confirm}
                    onChange={setConfirm}
                    placeholder="••••••••"
                  />
                </FormField>

                {fieldError ? (
                  <p className="form-field__error" role="alert">
                    {fieldError}
                  </p>
                ) : null}
                {formError ? (
                  <p className="form-field__error form-field__error--form" role="alert">
                    {formError}
                  </p>
                ) : null}

                <div className="member-auth__submit">
                  <SaveButton busy={submitting} busyLabel="Saving…">
                    Set password
                  </SaveButton>
                </div>
              </form>
            </>
          )}
        </div>
      </div>
    </main>
  )
}
