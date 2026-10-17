/**
 * Member sign-in — the unauthenticated entry point to the member portal.
 *
 * Errors stay generic: the API never reveals whether an account exists and
 * this page does not echo that detail either. Accounts are provisioned by the
 * lab team; there is no self-service registration.
 */

import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useMemberAuth } from '../../app/providers/MemberAuthProvider'
import { memberLogin } from '../../features/members/api'
import { isApiError, getErrorMessage } from '../../lib/errors/ApiError'
import { usePageMeta } from '../../lib/utils/seo'
import { FormField } from '../../components/form/FormField'
import { TextInput } from '../../components/form/TextInput'
import { PasswordInput } from '../../components/member/PasswordInput'
import { SaveButton } from '../../components/form/SaveButton'
import { PageLoader } from '../../components/ui/PageLoader'

interface LoginLocationState {
  from?: string
}

export default function MemberLoginPage() {
  usePageMeta({ title: 'Member sign in — Thridha Labs' })

  const { status, refresh } = useMemberAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const { from = '/member' } = (location.state as LoginLocationState | null) ?? {}

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const stateLocation = from.startsWith('/member') ? from : '/member'

  if (status === 'loading') {
    return <PageLoader label="Checking session…" />
  }

  if (status === 'authenticated') {
    return <Navigate to={stateLocation} replace />
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    const trimmedEmail = email.trim().toLowerCase()
    if (!trimmedEmail || !password) {
      setFieldError('Enter your email and password.')
      return
    }

    setSubmitting(true)
    setFormError(null)
    setFieldError(null)
    try {
      await memberLogin(trimmedEmail, password)
      await refresh()
      navigate(stateLocation, { replace: true })
    } catch (caught) {
      if (isApiError(caught) && caught.status === 401) {
        setFormError('Incorrect email or password.')
      } else if (isApiError(caught) && caught.status === 403) {
        setFormError('This account is disabled. Please contact the lab team.')
      } else if (isApiError(caught) && caught.status === 429) {
        setFormError('Too many attempts. Please wait a moment and try again.')
      } else {
        setFormError(getErrorMessage(caught, 'Unable to sign in. Please try again.'))
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
          <div className="member-auth__stack">
            <h1 className="member-auth__title">Member sign in</h1>
            <p className="member-auth__lead">Access your lab member portal.</p>
          </div>

          <form className="member-auth__form" onSubmit={handleSubmit} noValidate>
            <FormField id="member-login-email" label="Email" required>
              <TextInput
                id="member-login-email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={setEmail}
                placeholder="you@example.com"
              />
            </FormField>

            <FormField id="member-login-password" label="Password" required>
              <PasswordInput
                id="member-login-password"
                autoComplete="current-password"
                value={password}
                onChange={setPassword}
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
              <SaveButton busy={submitting} busyLabel="Signing in…">
                Sign in
              </SaveButton>
            </div>
          </form>

          <p className="member-auth__footer">
            Have a setup link? <Link to="/member/setup">Complete your onboarding</Link>.
          </p>
        </div>
      </div>
    </main>
  )
}
