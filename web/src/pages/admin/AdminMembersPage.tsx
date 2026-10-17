/**
 * Admin members — paginated, searchable list of lab member accounts with
 * onboarding resend, activation toggles and (owner-only) deletion.
 *
 * The list is server-driven: search, status filter, sort and pagination all map
 * to backend query parameters.
 */

import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { usePageMeta } from '../../lib/utils/seo'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { useAdminMembers } from '../../features/members/hooks'
import {
  deactivateMember,
  deleteMember,
  reactivateMember,
  resendMemberOnboarding,
} from '../../features/members/api'
import { memberStatusLabel, MEMBER_STATUS_CHIP } from '../../features/members/status'
import { useAuth } from '../../app/providers/AuthProvider'
import { canDelete } from '../../features/auth/rbac'
import { PageHeader } from '../../components/admin/PageHeader'
import { Pagination } from '../../components/admin/Pagination'
import { TextInput } from '../../components/form/TextInput'
import { Select } from '../../components/form/Select'
import { FormField } from '../../components/form/FormField'
import { ConfirmDialog } from '../../components/form/ConfirmDialog'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import { EmptyState } from '../../components/ui/EmptyState'
import type { MemberAdmin, MemberListQuery, MemberStatus } from '../../types/member'

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'pending_setup', label: 'Pending setup' },
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
]

function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString()
}

export default function AdminMembersPage() {
  usePageMeta({ title: 'Members — Admin — Thridha Labs' })

  const { user } = useAuth()
  const mayDelete = canDelete(user?.role)

  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<MemberStatus | ''>('')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')

  const query: MemberListQuery = useMemo(
    () => ({ page, page_size: 20, sort: 'created_at', order: 'desc', status, search }),
    [page, status, search],
  )

  const { data, loading, error, reload } = useAdminMembers(query)
  useAdminSessionIssue(error)

  const [pendingDelete, setPendingDelete] = useState<MemberAdmin | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  async function runAction(member: MemberAdmin, action: () => Promise<unknown>): Promise<void> {
    setBusyId(member.id)
    setActionError(null)
    try {
      await action()
      await reload()
    } catch (caught) {
      setActionError(getErrorMessage(caught, 'Could not complete that action.'))
    } finally {
      setBusyId(null)
    }
  }

  async function handleDelete(): Promise<void> {
    if (!pendingDelete) return
    const target = pendingDelete
    setBusyId(target.id)
    setActionError(null)
    try {
      await deleteMember(target.id)
      setPendingDelete(null)
      await reload()
    } catch (caught) {
      setActionError(getErrorMessage(caught, 'Could not delete the member.'))
    } finally {
      setBusyId(null)
    }
  }

  function handleSearchSubmit(event: React.FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    setPage(1)
    setSearch(searchInput.trim())
  }

  const rows = data?.items ?? []

  return (
    <div>
      <PageHeader
        eyebrow="People"
        title="Members"
        description="Lab member accounts. Membership is invite-only; members are provisioned here."
        actionLabel="Add member"
        actionTo="/admin/members/new"
      />

      <form className="admin-toolbar" onSubmit={handleSearchSubmit}>
        <TextInput
          id="members-search"
          aria-label="Search members"
          placeholder="Search name, email or ID…"
          value={searchInput}
          onChange={setSearchInput}
          className="admin-toolbar__search"
        />
        <button type="submit" className="btn btn--ghost btn--sm">
          Search
        </button>
        <FormField id="members-status" label="Status">
          <Select
            id="members-status"
            aria-label="Filter by status"
            options={STATUS_OPTIONS}
            value={status}
            onChange={(value) => {
              setPage(1)
              setStatus(value as MemberStatus | '')
            }}
          />
        </FormField>
      </form>

      {actionError ? (
        <p className="form-field__error form-field__error--form" role="alert">
          {actionError}
        </p>
      ) : null}

      {loading ? <ContentSkeleton rows={4} /> : null}
      {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}
      {!loading && !error && rows.length === 0 ? (
        search || status ? (
          <EmptyState title="No matches" description="Try a different search or clear the filter." />
        ) : (
          <EmptyState title="No members yet" description="Add your first member to get started." />
        )
      ) : null}

      {rows.length > 0 ? (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Member</th>
                <th>Status</th>
                <th>Profile</th>
                <th>Onboarding</th>
                <th>Last sign-in</th>
                <th className="admin-table__actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((member) => {
                const busy = busyId === member.id
                return (
                  <tr key={member.id}>
                    <td>
                      <Link to={`/admin/members/${member.id}`} className="admin-table__name">
                        {member.full_name || member.email}
                      </Link>
                      <span className="admin-table__sub mono">{member.member_id}</span>
                      <span className="admin-table__sub">{member.email}</span>
                    </td>
                    <td>
                      <span className={`chip ${MEMBER_STATUS_CHIP[member.status]}`}>
                        {memberStatusLabel(member.status)}
                      </span>
                    </td>
                    <td>{member.profile_complete ? <span className="chip chip--ok">Complete</span> : <span className="chip chip--muted">Incomplete</span>}</td>
                    <td>
                      {member.onboarding_completed_at ? (
                        <span className="chip chip--ok">Completed</span>
                      ) : member.onboarding_sent ? (
                        <span className="chip chip--warn">Sent</span>
                      ) : (
                        <span className="chip chip--muted">Not sent</span>
                      )}
                    </td>
                    <td>{formatDate(member.last_login_at)}</td>
                    <td className="admin-table__actions">
                      <Link className="btn btn--ghost btn--sm" to={`/admin/members/${member.id}`}>
                        Edit
                      </Link>
                      {!member.onboarding_completed_at ? (
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          disabled={busy}
                          onClick={() => void runAction(member, () => resendMemberOnboarding(member.id))}
                        >
                          Resend
                        </button>
                      ) : null}
                      {member.status === 'inactive' ? (
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          disabled={busy}
                          onClick={() => void runAction(member, () => reactivateMember(member.id))}
                        >
                          Reactivate
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          disabled={busy}
                          onClick={() => void runAction(member, () => deactivateMember(member.id))}
                        >
                          Deactivate
                        </button>
                      )}
                      {mayDelete ? (
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          disabled={busy}
                          onClick={() => setPendingDelete(member)}
                        >
                          Delete
                        </button>
                      ) : null}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : null}

      {rows.length > 0 ? (
        <Pagination
          page={data?.page ?? 1}
          pages={data?.pages ?? 1}
          total={data?.total ?? 0}
          onChange={setPage}
        />
      ) : null}

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete this member?"
        body={
          pendingDelete
            ? `${pendingDelete.full_name || pendingDelete.email} (${pendingDelete.member_id}) will be permanently removed, along with any profile picture they uploaded. This cannot be undone.`
            : ''
        }
        confirmLabel="Delete"
        cancelLabel="Cancel"
        danger
        busy={pendingDelete !== null && busyId === pendingDelete.id}
        onConfirm={() => void handleDelete()}
        onCancel={() => {
          if (!busyId) setPendingDelete(null)
        }}
      />
    </div>
  )
}