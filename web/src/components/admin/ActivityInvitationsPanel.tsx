/**
 * ActivityInvitationsPanel — searchable, paginated member selection for sending
 * project invitations.
 *
 * Only rendered for published project activities. The list is server-driven
 * (search + pagination map to the `/members` query), so it scales beyond one
 * page. Selections persist across pages and search changes, are keyed by member
 * id (no duplicates), and stay assignable to a project role until sent.
 *
 * Inviting never auto-adds an active participant: selected members are recorded
 * as `invited` and the admin confirms replies manually on the roster below.
 */

import { useEffect, useMemo, useState } from 'react'
import { Checkbox } from '../form/Checkbox'
import { Textarea } from '../form/Textarea'
import { TextInput } from '../form/TextInput'
import { Select } from '../form/Select'
import { SaveButton } from '../form/SaveButton'
import { Pagination } from '../admin/Pagination'
import { ContentSkeleton } from '../ui/ContentSkeleton'
import { EmptyState } from '../ui/EmptyState'
import { ErrorState } from '../ui/ErrorState'
import { useAdminMembers } from '../../features/members/hooks'
import { useActivityParticipants } from '../../features/activities/hooks'
import { inviteToActivity } from '../../features/activities/api'
import { memberStatusLabel, MEMBER_STATUS_CHIP } from '../../features/members/status'
import { PARTICIPATION_STATUS_LABELS } from '../../features/activities/labels'
import { getErrorMessage } from '../../lib/errors/ApiError'
import type { InvitationItem, InvitationResult, ParticipationStatus } from '../../types/activity'
import type { MemberAdmin } from '../../types/member'

const PAGE_SIZE = 10
const SEARCH_DEBOUNCE_MS = 300

/** Participation states that already occupy a slot on the project. */
const BLOCKING_PARTICIPATION: ParticipationStatus[] = ['invited', 'interested', 'confirmed']

interface SelectedMember {
  member: MemberAdmin
  role: string
}

export interface ActivityInvitationsPanelProps {
  activityId: string
  /** Roles offered by the activity (used to assign a role per invitee). */
  roleOptions?: string[]
  onInvited: () => void
}

/** A reason this member cannot be invited right now, or null when eligible. */
function blockReason(member: MemberAdmin, participation: ParticipationStatus | null): string | null {
  if (member.status === 'inactive') return 'Inactive account'
  if (member.status === 'pending_setup') return 'Setup incomplete'
  if (participation && BLOCKING_PARTICIPATION.includes(participation)) {
    return PARTICIPATION_STATUS_LABELS[participation]
  }
  return null
}

export function ActivityInvitationsPanel({
  activityId,
  roleOptions = [],
  onInvited,
}: ActivityInvitationsPanelProps) {
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)

  // Debounce the search box and jump back to the first page when it changes.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [searchInput])

  const query = useMemo(
    () => ({ page, page_size: PAGE_SIZE, sort: 'created_at', order: 'desc' as const, search }),
    [page, search],
  )
  const members = useAdminMembers(query)
  const participants = useActivityParticipants(activityId, { page: 1, page_size: 100 })

  const [selected, setSelected] = useState<Record<string, SelectedMember>>({})
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<InvitationResult | null>(null)

  // member internal id -> current participation status (if any)
  const participationById = useMemo(() => {
    const map: Record<string, ParticipationStatus> = {}
    for (const p of participants.data?.items ?? []) {
      map[p.member_id] = p.status
    }
    return map
  }, [participants.data])

  const memberList = members.data?.items ?? []
  const selectedList = useMemo(() => Object.values(selected), [selected])
  const selectedCount = selectedList.length

  function toggle(member: MemberAdmin, checked: boolean): void {
    setSelected((prev) => {
      if (!checked) {
        const next = { ...prev }
        delete next[member.id]
        return next
      }
      return { ...prev, [member.id]: { member, role: prev[member.id]?.role ?? '' } }
    })
  }

  function setRole(memberId: string, role: string): void {
    setSelected((prev) => (prev[memberId] ? { ...prev, [memberId]: { ...prev[memberId], role } } : prev))
  }

  function removeSelected(memberId: string): void {
    setSelected((prev) => {
      const next = { ...prev }
      delete next[memberId]
      return next
    })
  }

  async function send(): Promise<void> {
    if (selectedCount === 0) {
      setError('Select at least one member to invite.')
      return
    }
    setSending(true)
    setError(null)
    setResult(null)
    const invitations: InvitationItem[] = selectedList.map(({ member, role }) => ({
      member_id: member.id,
      role: role.trim() || null,
    }))
    try {
      const outcome = await inviteToActivity(activityId, {
        invitations,
        subject: subject.trim() || null,
        message: message.trim() || null,
      })
      setResult(outcome)
      setSelected({})
      onInvited()
      await participants.reload()
    } catch (caught) {
      setError(getErrorMessage(caught, 'Could not send the invitations.'))
    } finally {
      setSending(false)
    }
  }

  const roleSelectOptions = [
    { value: '', label: 'No role' },
    ...roleOptions.map((role) => ({ value: role, label: role })),
  ]

  return (
    <section className="admin-section">
      <h2 className="admin-section__title">Invite members</h2>
      <p className="admin-section__hint">
        Search by name, email or role, then pick the members to invite. Invited members are recorded
        as <strong>Invited</strong> — they are not active until they respond and you confirm them on
        the roster below.
      </p>

      <div className="admin-toolbar invite-toolbar">
        <TextInput
          id="invite-member-search"
          aria-label="Search members"
          placeholder="Search name, email or role…"
          value={searchInput}
          onChange={setSearchInput}
          className="admin-toolbar__search"
        />
        {searchInput ? (
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => setSearchInput('')}
          >
            Clear
          </button>
        ) : null}
        <span className="invite-toolbar__total" role="status">
          {members.loading
            ? 'Searching…'
            : `${members.data?.total ?? 0} member${(members.data?.total ?? 0) === 1 ? '' : 's'}`}
        </span>
      </div>

      {selectedCount > 0 ? (
        <div className="invite-selected" aria-label="Selected members">
          <div className="invite-selected__head">
            <strong>{selectedCount} selected</strong>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => setSelected({})}
            >
              Clear all
            </button>
          </div>
          <ul className="invite-selected__list">
            {selectedList.map(({ member, role }) => (
              <li key={member.id} className="invite-selected__item">
                <span className="invite-selected__name">
                  {member.full_name || member.email}
                  <span className="admin-table__sub">{member.email}</span>
                </span>
                {roleOptions.length > 0 ? (
                  <Select
                    aria-label={`Role for ${member.full_name || member.email}`}
                    className="invite-selected__role"
                    options={roleSelectOptions}
                    value={role}
                    onChange={(value) => setRole(member.id, value)}
                  />
                ) : (
                  <TextInput
                    aria-label={`Role for ${member.full_name || member.email}`}
                    className="invite-selected__role"
                    placeholder="Role (e.g. Frontend Developer)"
                    value={role}
                    onChange={(value) => setRole(member.id, value)}
                  />
                )}
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  aria-label={`Remove ${member.full_name || member.email}`}
                  onClick={() => removeSelected(member.id)}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {members.loading ? <ContentSkeleton rows={3} /> : null}
      {members.error && !members.loading ? (
        <ErrorState error={members.error} onRetry={members.reload} />
      ) : null}

      {!members.loading && !members.error && memberList.length === 0 ? (
        <EmptyState
          title={search ? 'No matching members' : 'No members yet'}
          description={
            search
              ? 'Try a different name, email or role.'
              : 'Add members from the Members page to invite them.'
          }
        />
      ) : null}

      {!members.loading && !members.error && memberList.length > 0 ? (
        <div className="admin-table-wrap">
          <table className="admin-table invite-table">
            <thead>
              <tr>
                <th className="invite-table__check">Select</th>
                <th>Member</th>
                <th>Role</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {memberList.map((member) => {
                const participation = participationById[member.id] ?? null
                const blocked = blockReason(member, participation)
                const isSelected = Boolean(selected[member.id])
                return (
                  <tr key={member.id} className={blocked && !isSelected ? 'invite-table__row--blocked' : ''}>
                    <td className="invite-table__check">
                      <Checkbox
                        id={`invite-${member.id}`}
                        label={`Select ${member.full_name || member.email}`}
                        checked={isSelected}
                        disabled={Boolean(blocked)}
                        onChange={(checked) => toggle(member, checked)}
                        className="invite-table__checkbox"
                      />
                    </td>
                    <td>
                      <span className="admin-table__name">{member.full_name || member.email}</span>
                      <span className="admin-table__sub">{member.email}</span>
                      <span className="admin-table__sub mono">{member.member_id}</span>
                    </td>
                    <td>{member.role_label || '—'}</td>
                    <td>
                      <span className={`chip ${MEMBER_STATUS_CHIP[member.status]}`}>
                        {memberStatusLabel(member.status)}
                      </span>
                      {blocked && participation ? (
                        <span className="chip chip--part invite-table__part">
                          {PARTICIPATION_STATUS_LABELS[participation]}
                        </span>
                      ) : null}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : null}

      {!members.loading && !members.error && memberList.length > 0 ? (
        <Pagination
          page={members.data?.page ?? page}
          pages={members.data?.pages ?? 1}
          total={members.data?.total ?? 0}
          onChange={setPage}
        />
      ) : null}

      <details className="invite-message">
        <summary>Customise the invitation email (optional)</summary>
        <div className="admin-form__row">
          <TextInput
            aria-label="Invitation subject"
            placeholder="Optional subject override"
            value={subject}
            onChange={setSubject}
          />
        </div>
        <Textarea
          aria-label="Invitation message"
          rows={3}
          placeholder="Optional message override"
          value={message}
          onChange={setMessage}
        />
      </details>

      {error ? (
        <p className="form-field__error form-field__error--form" role="alert">
          {error}
        </p>
      ) : null}

      {result ? (
        <div className="invite-result" role="status">
          <p>
            Invited {result.invited}, re-invited {result.re_invited}, emails sent {result.emails_sent}
            {result.email_failures > 0 ? ` · ${result.email_failures} email failure(s)` : ''}.
          </p>
          {result.skipped.length > 0 ? (
            <p className="admin-section__hint">Skipped: {result.skipped.join(', ')}</p>
          ) : null}
          {result.errors.length > 0 ? (
            <p className="form-field__error">{result.errors.join('; ')}</p>
          ) : null}
        </div>
      ) : null}

      <SaveButton busy={sending} disabled={selectedCount === 0} onClick={() => void send()}>
        {selectedCount > 0 ? `Send ${selectedCount} invitation(s)` : 'Send invitations'}
      </SaveButton>
    </section>
  )
}
