/**
 * Admin member editor — create (`/admin/members/new`) and edit
 * (`/admin/members/:memberId`).
 *
 * Admin-managed fields (email, full name, role label, joined opportunity and
 * internal note) are editable here; members manage their own public profile in
 * the member portal. Lifecycle actions (resend, deactivate/reactivate, delete)
 * live on the edit view.
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { useBeforeUnload } from '../../lib/hooks/useBeforeUnload'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { useAdminMember } from '../../features/members/hooks'
import {
  createMember,
  updateMember,
  resendMemberOnboarding,
  deactivateMember,
  reactivateMember,
  deleteMember,
} from '../../features/members/api'
import { memberStatusLabel, MEMBER_STATUS_CHIP } from '../../features/members/status'
import { useAdminOpportunities } from '../../features/careers/hooks'
import { useAuth } from '../../app/providers/AuthProvider'
import { canDelete } from '../../features/auth/rbac'
import { PageHeader } from '../../components/admin/PageHeader'
import { FormField } from '../../components/form/FormField'
import { TextInput } from '../../components/form/TextInput'
import { Textarea } from '../../components/form/Textarea'
import { Select } from '../../components/form/Select'
import { FormActions } from '../../components/form/FormActions'
import { SaveButton } from '../../components/form/SaveButton'
import { ConfirmDialog } from '../../components/form/ConfirmDialog'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import type { MemberAdmin } from '../../types/member'

function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString()
}

export default function AdminMemberEditPage() {
  const { memberId = 'new' } = useParams()
  const isNew = memberId === 'new'
  usePageMeta({ title: `${isNew ? 'Add member' : 'Edit member'} — Admin — Thridha Labs` })

  const navigate = useNavigate()
  const { user } = useAuth()
  const mayDelete = canDelete(user?.role)
  const { data, loading, error, reload } = useAdminMember(isNew ? undefined : memberId)
  useAdminSessionIssue(error)

  const { data: opportunitiesData } = useAdminOpportunities({ page_size: 100 })
  const opportunityOptions = useMemo(
    () => [
      { value: '', label: 'None' },
      ...(opportunitiesData?.items ?? []).map((opportunity) => ({
        value: opportunity.id,
        label: opportunity.title,
      })),
    ],
    [opportunitiesData],
  )

  const [form, setForm] = useState({
    email: '',
    full_name: '',
    role_label: '',
    joined_opportunity_id: '',
    internal_note: '',
  })
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionBusy, setActionBusy] = useState(false)
  const [discardOpen, setDiscardOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)

  useBeforeUnload(dirty)

  const hydrated = useRef(false)
  useEffect(() => {
    if (!data || hydrated.current) return
    hydrated.current = true
    setForm({
      email: data.email,
      full_name: data.full_name ?? '',
      role_label: data.role_label ?? '',
      joined_opportunity_id: data.joined_opportunity_id ?? '',
      internal_note: data.internal_note ?? '',
    })
    setDirty(false)
  }, [data])

  function patch(p: Partial<typeof form>): void {
    setForm((prev) => ({ ...prev, ...p }))
    setDirty(true)
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    const payload = {
      email: form.email.trim().toLowerCase(),
      full_name: form.full_name.trim() || null,
      role_label: form.role_label.trim() || null,
      joined_opportunity_id: form.joined_opportunity_id || null,
      internal_note: form.internal_note.trim() || null,
    }
    setSaving(true)
    setSaveError(null)
    try {
      if (isNew) {
        const created = await createMember(payload)
        setDirty(false)
        navigate(`/admin/members/${created.id}`)
      } else {
        await updateMember(memberId, payload)
        setDirty(false)
        hydrated.current = false
        await reload()
      }
    } catch (caught) {
      setSaveError(getErrorMessage(caught, 'Could not save the member.'))
    } finally {
      setSaving(false)
    }
  }

  async function runAction(action: () => Promise<unknown>, fallback: string): Promise<void> {
    setActionBusy(true)
    setActionError(null)
    try {
      await action()
      hydrated.current = false
      await reload()
    } catch (caught) {
      setActionError(getErrorMessage(caught, fallback))
    } finally {
      setActionBusy(false)
    }
  }

  async function handleDelete(): Promise<void> {
    setActionBusy(true)
    setActionError(null)
    try {
      await deleteMember(memberId)
      setDeleteOpen(false)
      setDirty(false)
      navigate('/admin/members')
    } catch (caught) {
      setActionError(getErrorMessage(caught, 'Could not delete the member.'))
    } finally {
      setActionBusy(false)
    }
  }

  function handleCancel(): void {
    if (dirty) {
      setDiscardOpen(true)
    } else {
      navigate('/admin/members')
    }
  }

  if (!isNew && loading) {
    return <ContentSkeleton rows={5} />
  }

  if (!isNew && error) {
    return <ErrorState error={error} onRetry={reload} />
  }

  const member = data as MemberAdmin | undefined

  return (
    <div>
      <PageHeader
        eyebrow="People"
        title={isNew ? 'Add member' : 'Edit member'}
        description={
          isNew
            ? 'Create a member account and email an onboarding link.'
            : `Editing ${member?.full_name || member?.email || 'member'}.`
        }
      />

      <form className="admin-form" onSubmit={handleSubmit} noValidate>
        <section className="admin-section">
          <h2 className="admin-section__title">Account</h2>
          <FormField id="member-email" label="Email" hint="Used for sign-in and onboarding" required>
            <TextInput
              id="member-email"
              type="email"
              value={form.email}
              onChange={(value) => patch({ email: value })}
              placeholder="member@example.com"
            />
          </FormField>
          <FormField id="member-full-name" label="Full name">
            <TextInput
              id="member-full-name"
              value={form.full_name}
              onChange={(value) => patch({ full_name: value })}
              placeholder="Ada Lovelace"
            />
          </FormField>
          <FormField id="member-role-label" label="Role label" hint="Display only, not permissions">
            <TextInput
              id="member-role-label"
              value={form.role_label}
              onChange={(value) => patch({ role_label: value })}
              placeholder="Research Member"
            />
          </FormField>
          <FormField id="member-opportunity" label="Joined opportunity">
            <Select
              id="member-opportunity"
              options={opportunityOptions}
              value={form.joined_opportunity_id}
              onChange={(value) => patch({ joined_opportunity_id: value })}
            />
          </FormField>
          <FormField id="member-note" label="Internal note" hint="Admin-only">
            <Textarea
              id="member-note"
              rows={3}
              value={form.internal_note}
              onChange={(value) => patch({ internal_note: value })}
            />
          </FormField>
        </section>

        {!isNew && member ? (
          <section className="admin-section">
            <h2 className="admin-section__title">Status</h2>
            <div className="card account-card" style={{ maxWidth: '520px' }}>
              <dl className="account-list">
                <div className="account-list__row">
                  <dt>Member ID</dt>
                  <dd className="mono">{member.member_id}</dd>
                </div>
                <div className="account-list__row">
                  <dt>Status</dt>
                  <dd>
                    <span className={`chip ${MEMBER_STATUS_CHIP[member.status]}`}>
                      {memberStatusLabel(member.status)}
                    </span>
                  </dd>
                </div>
                <div className="account-list__row">
                  <dt>Profile</dt>
                  <dd>
                    {member.profile_complete ? (
                      <span className="chip chip--ok">Complete</span>
                    ) : (
                      <span className="chip chip--muted">Incomplete</span>
                    )}
                  </dd>
                </div>
                <div className="account-list__row">
                  <dt>Onboarding</dt>
                  <dd>
                    {member.onboarding_completed_at
                      ? `Completed ${formatDate(member.onboarding_completed_at)}`
                      : member.onboarding_sent
                        ? 'Link sent'
                        : 'Not sent'}
                  </dd>
                </div>
                <div className="account-list__row">
                  <dt>Last sign-in</dt>
                  <dd>{formatDate(member.last_login_at)}</dd>
                </div>
                <div className="account-list__row">
                  <dt>Created</dt>
                  <dd>{formatDate(member.created_at)}</dd>
                </div>
              </dl>
            </div>
            <p className="admin-section__hint" style={{ marginTop: 'var(--space-4)' }}>
              Members control their own public profile (bio, skills, interests, links) from the
              member portal. Full name and email are managed here.
            </p>
          </section>
        ) : null}

        {saveError ? (
          <p className="form-field__error form-field__error--form" role="alert">
            {saveError}
          </p>
        ) : null}
        {dirty ? (
          <p className="admin-form__dirty" role="status">
            Unsaved changes.
          </p>
        ) : null}

        <FormActions onCancel={handleCancel}>
          <SaveButton busy={saving}>{isNew ? 'Create member' : 'Save changes'}</SaveButton>
        </FormActions>
      </form>

      {!isNew && member ? (
        <section className="admin-section">
          <h2 className="admin-section__title">Lifecycle</h2>
          {actionError ? (
            <p className="form-field__error form-field__error--form" role="alert">
              {actionError}
            </p>
          ) : null}
          <div className="form-actions">
            {!member.onboarding_completed_at ? (
              <button
                type="button"
                className="btn btn--ghost"
                disabled={actionBusy}
                onClick={() =>
                  void runAction(
                    () => resendMemberOnboarding(memberId),
                    'Could not resend the onboarding link.',
                  )
                }
              >
                Resend onboarding link
              </button>
            ) : null}
            {member.status === 'inactive' ? (
              <button
                type="button"
                className="btn btn--ghost"
                disabled={actionBusy}
                onClick={() =>
                  void runAction(
                    () => reactivateMember(memberId),
                    'Could not reactivate the member.',
                  )
                }
              >
                Reactivate
              </button>
            ) : (
              <button
                type="button"
                className="btn btn--ghost"
                disabled={actionBusy}
                onClick={() =>
                  void runAction(
                    () => deactivateMember(memberId),
                    'Could not deactivate the member.',
                  )
                }
              >
                Deactivate
              </button>
            )}
            {mayDelete ? (
              <button
                type="button"
                className="btn btn--danger"
                disabled={actionBusy}
                onClick={() => setDeleteOpen(true)}
              >
                Delete member
              </button>
            ) : null}
          </div>
        </section>
      ) : null}

      <p style={{ marginTop: 'var(--space-5)' }}>
        <Link className="btn btn--ghost btn--sm" to="/admin/members">
          Back to members
        </Link>
      </p>

      <ConfirmDialog
        open={discardOpen}
        title="Discard unsaved changes?"
        body="Your edits have not been saved and will be lost."
        confirmLabel="Discard"
        cancelLabel="Keep editing"
        danger
        onConfirm={() => navigate('/admin/members')}
        onCancel={() => setDiscardOpen(false)}
      />

      <ConfirmDialog
        open={deleteOpen}
        title="Delete this member?"
        body="This permanently removes the member account and any profile picture they uploaded. This cannot be undone."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        danger
        busy={actionBusy}
        onConfirm={() => void handleDelete()}
        onCancel={() => {
          if (!actionBusy) setDeleteOpen(false)
        }}
      />
    </div>
  )
}