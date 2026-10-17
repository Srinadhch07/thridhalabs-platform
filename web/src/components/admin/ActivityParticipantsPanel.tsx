/**
 * ActivityParticipantsPanel — admin management of an activity's participation
 * records. Invited members (project activities) and self-registered members
 * (programmes/hackathons) are shown together so the admin has one roster.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Select } from '../form/Select'
import { TextInput } from '../form/TextInput'
import { SaveButton } from '../form/SaveButton'
import { ContentSkeleton } from '../ui/ContentSkeleton'
import { EmptyState } from '../ui/EmptyState'
import { ErrorState } from '../ui/ErrorState'
import { useActivityParticipants } from '../../features/activities/hooks'
import { updateActivityParticipant } from '../../features/activities/api'
import { PARTICIPATION_STATUS_LABELS } from '../../features/activities/labels'
import { getErrorMessage } from '../../lib/errors/ApiError'
import type { ActivityParticipant, ParticipationStatus } from '../../types/activity'

const STATUS_OPTIONS = (Object.keys(PARTICIPATION_STATUS_LABELS) as ParticipationStatus[]).map(
  (value) => ({ value, label: PARTICIPATION_STATUS_LABELS[value] }),
)

function ParticipantRow({
  participant,
  activityId,
  onSaved,
}: {
  participant: ActivityParticipant
  activityId: string
  onSaved: () => void
}) {
  const [status, setStatus] = useState<ParticipationStatus>(participant.status)
  const [role, setRole] = useState(participant.role ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const dirty = status !== participant.status || role !== (participant.role ?? '')

  async function save(): Promise<void> {
    setSaving(true)
    setError(null)
    try {
      await updateActivityParticipant(activityId, participant.id, {
        status,
        role: role.trim() || null,
      })
      onSaved()
    } catch (caught) {
      setError(getErrorMessage(caught, 'Could not update the participant.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <tr>
      <td>
        <span className="admin-table__name">
          {participant.member_name ?? participant.member_readable_id}
        </span>
        <span className="admin-table__sub mono">{participant.member_readable_id}</span>
        {error ? (
          <span className="form-field__error" role="alert">
            {error}
          </span>
        ) : null}
      </td>
      <td>
        <span className="chip">{participant.source === 'invited' ? 'Invited' : 'Self'}</span>
      </td>
      <td>
        <Select
          aria-label={`Status for ${participant.member_readable_id}`}
          options={STATUS_OPTIONS}
          value={status}
          onChange={(value) => setStatus(value as ParticipationStatus)}
        />
      </td>
      <td>
        <TextInput
          aria-label={`Role for ${participant.member_readable_id}`}
          value={role}
          onChange={setRole}
          placeholder="Role"
        />
      </td>
      <td className="admin-table__actions">
        <SaveButton busy={saving} disabled={!dirty} onClick={() => void save()}>
          Save
        </SaveButton>
      </td>
    </tr>
  )
}

export interface ActivityParticipantsPanelProps {
  activityId: string
}

export function ActivityParticipantsPanel({ activityId }: ActivityParticipantsPanelProps) {
  const [statusFilter, setStatusFilter] = useState<'' | ParticipationStatus>('')
  const { data, loading, error, reload } = useActivityParticipants(activityId, {
    page: 1,
    page_size: 100,
    status: statusFilter || undefined,
  })

  return (
    <section className="admin-section">
      <div className="admin-section__head">
        <h2 className="admin-section__title">Participants</h2>
        <Select
          aria-label="Filter participants by status"
          placeholder="All statuses"
          options={STATUS_OPTIONS}
          value={statusFilter}
          onChange={(value) => setStatusFilter(value as '' | ParticipationStatus)}
        />
      </div>

      {loading ? <ContentSkeleton rows={3} /> : null}
      {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}
      {!loading && !error && (data?.items.length ?? 0) === 0 ? (
        <EmptyState
          title="No participants yet"
          description="Invitations and self-registrations will appear here."
        />
      ) : null}

      {!loading && !error && (data?.items.length ?? 0) > 0 ? (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Member</th>
                <th>Source</th>
                <th>Status</th>
                <th>Role</th>
                <th className="admin-table__actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data!.items.map((participant) => (
                <ParticipantRow
                  key={participant.id}
                  participant={participant}
                  activityId={activityId}
                  onSaved={reload}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <p className="admin-section__hint">
        Confirmed participants count toward the activity roster.{' '}
        <Link to="/admin/members">Manage members</Link>.
      </p>
    </section>
  )
}
