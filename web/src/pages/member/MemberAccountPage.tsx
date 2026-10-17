/**
 * Member account — session details, password management and sign-out.
 *
 * Member IDs and emails are provisioned by the lab team (read-only here).
 * Changing the password does not revoke the current session.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMemberAuth } from '../../app/providers/MemberAuthProvider'
import { useMemberSessionIssue } from '../../lib/hooks/useMemberSession'
import { useAsync } from '../../lib/hooks/useAsync'
import { getMemberProfile, changeMemberPassword } from '../../features/members/api'
import { memberStatusLabel, MEMBER_STATUS_CHIP } from '../../features/members/status'
import { isApiError, getErrorMessage } from '../../lib/errors/ApiError'
import { usePageMeta } from '../../lib/utils/seo'
import { MemberPageHeader } from '../../components/member/MemberPageHeader'
import { MemberCard } from '../../components/member/MemberCard'
import { MemberAvatar } from '../../components/member/MemberAvatar'
import { FormField } from '../../components/form/FormField'
import { PasswordInput } from '../../components/member/PasswordInput'
import { FormActions } from '../../components/form/FormActions'
import { SaveButton } from '../../components/form/SaveButton'
import { PageLoader } from '../../components/ui/PageLoader'
import { ErrorState } from '../../components/ui/ErrorState'

export default function MemberAccountPage() {
  usePageMeta({ title: 'Account — Member portal — Thridha Labs' })

  const { member, signOut } = useMemberAuth()
  const { data, loading, error, reload } = useAsync(() => getMemberProfile(), [])
  useMemberSessionIssue(error)
  const navigate = useNavigate()

  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  async function handleSignOut(): Promise<void> {
    await signOut()
    navigate('/member/login', { replace: true })
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    if (next.length < 10) {
      setFieldError('Choose a new password of at least 10 characters.')
      return
    }
    if (next !== confirm) {
      setFieldError('The new passwords do not match.')
      return
    }

    setSubmitting(true)
    setFieldError(null)
    setFormError(null)
    setNotice(null)
    try {
      await changeMemberPassword(current, next)
      setCurrent('')
      setNext('')
      setConfirm('')
      setNotice('Password updated.')
    } catch (caught) {
      if (isApiError(caught) && caught.status === 401) {
        setFormError('Your current password is incorrect.')
      } else if (isApiError(caught) && caught.status === 400 && caught.code === 'PASSWORD_NOT_SET') {
        setFormError('Your account has no password yet. Use your setup link first.')
      } else if (isApiError(caught) && caught.status === 400 && caught.code === 'PASSWORD_UNCHANGED') {
        setFormError('Choose a password different from your current one.')
      } else if (isApiError(caught) && caught.status === 429) {
        setFormError('Too many attempts. Please wait a moment and try again.')
      } else {
        setFormError(getErrorMessage(caught, 'Could not change your password.'))
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return <PageLoader label="Loading account…" />
  }

  if (error) {
    return <ErrorState error={error} onRetry={reload} />
  }

  const displayName = data?.full_name || member?.full_name || 'Member'
  const status = data?.status ?? member?.status

  return (
    <div className="member-page">
      <MemberPageHeader title="Account Settings" description="Your membership and sign-in." />

      <div className="member-stack member-form">
        <MemberCard>
          <div className="member-profile-head">
            <MemberAvatar
              name={displayName}
              mediaId={data?.profile.picture_media_id ?? null}
              size="lg"
            />
            <div className="member-profile-head__meta">
              <h2 className="member-profile-head__name">{displayName}</h2>
              <span className="member-profile-head__sub">{data?.role_label ?? 'Lab member'}</span>
              {status ? (
                <span className={`chip ${MEMBER_STATUS_CHIP[status]}`}>
                  {memberStatusLabel(status)}
                </span>
              ) : null}
            </div>
          </div>

          <hr className="member-divider" />

          <dl className="member-meta">
            <div className="member-meta__row">
              <dt>Member ID</dt>
              <dd className="mono">{member?.member_id}</dd>
            </div>
            <div className="member-meta__row">
              <dt>Email</dt>
              <dd>{member?.email}</dd>
            </div>
            <div className="member-meta__row">
              <dt>Role label</dt>
              <dd>{data?.role_label ?? '—'}</dd>
            </div>
          </dl>

          <p className="member-card__desc">
            Member IDs and emails are managed by the lab team. Contact them if anything needs to
            change.
          </p>

          <div className="member-account-signout">
            <button type="button" className="btn btn--ghost" onClick={() => void handleSignOut()}>
              Sign out
            </button>
          </div>
        </MemberCard>

        <MemberCard title="Change password" description="Use at least 10 characters.">
          <form onSubmit={handleSubmit} noValidate>
            <div className="member-stack" style={{ gap: 'var(--space-4)' }}>
              <FormField id="member-current-password" label="Current password" required>
                <PasswordInput
                  id="member-current-password"
                  autoComplete="current-password"
                  value={current}
                  onChange={setCurrent}
                />
              </FormField>
              <FormField id="member-new-password" label="New password" hint="At least 10 characters" required>
                <PasswordInput
                  id="member-new-password"
                  autoComplete="new-password"
                  value={next}
                  onChange={setNext}
                />
              </FormField>
              <FormField id="member-confirm-password" label="Confirm new password" required>
                <PasswordInput
                  id="member-confirm-password"
                  autoComplete="new-password"
                  value={confirm}
                  onChange={setConfirm}
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
              {notice ? (
                <p className="admin-form__dirty" role="status">
                  {notice}
                </p>
              ) : null}

              <FormActions>
                <SaveButton busy={submitting} busyLabel="Updating…">
                  Update password
                </SaveButton>
              </FormActions>
            </div>
          </form>
        </MemberCard>
      </div>
    </div>
  )
}
