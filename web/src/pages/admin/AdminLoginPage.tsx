/**
 * Admin sign-in — the only unauthenticated surface in the admin namespace.
 *
 * Errors are deliberately generic: the API never reveals whether an account
 * exists, and this page does not echo that detail either.
 */

import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../app/providers/AuthProvider'
import { login } from '../../features/auth/api'
import { isApiError, getErrorMessage } from '../../lib/errors/ApiError'
import { usePageMeta } from '../../lib/utils/seo'
import { FormField } from '../../components/form/FormField'
import { TextInput } from '../../components/form/TextInput'
import { SaveButton } from '../../components/form/SaveButton'
import { PageLoader } from '../../components/ui/PageLoader'

interface LoginLocationState {
  from?: string
}

export default function AdminLoginPage() {
  usePageMeta({ title: 'Admin sign in — Thridha Labs' })

  const { status, refresh } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const { from = '/admin' } = (location.state as LoginLocationState | null) ?? {}

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const stateLocation = from.startsWith('/admin') ? from : '/admin'

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
      await login(trimmedEmail, password)
      await refresh()
      navigate(stateLocation, { replace: true })
    } catch (caught) {
      if (isApiError(caught) && caught.status === 401) {
        setFormError('Incorrect email or password.')
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
    <div className="site-shell">
      <main className="admin-login">
        <div className="card admin-login__card">
          <p className="eyebrow">Thridha Labs</p>
          <h1 style={{ fontSize: 'var(--fs-lg)' }}>Sign in</h1>
          <p className="admin-login__lead">Access the control center.</p>

          <form onSubmit={handleSubmit} noValidate>
            <FormField id="login-email" label="Email" required>
              <TextInput
                id="login-email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={setEmail}
                placeholder="you@example.com"
              />
            </FormField>

            <FormField id="login-password" label="Password" required>
              <TextInput
                id="login-password"
                type="password"
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

            <div className="form-actions">
              <SaveButton busy={submitting} busyLabel="Signing in…">
                Sign in
              </SaveButton>
            </div>
          </form>
        </div>
      </main>
    </div>
  )
}