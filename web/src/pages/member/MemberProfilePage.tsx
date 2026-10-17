/**
 * Member profile — self-service editor for the member's own profile.
 *
 * Full name is admin-managed and therefore read-only here; members edit their
 * public details, skills/interests and avatar. Skills and interests are entered
 * as comma-separated values and sent as arrays.
 */

import { useEffect, useRef, useState } from 'react'
import { useMemberAuth } from '../../app/providers/MemberAuthProvider'
import { useMemberSessionIssue } from '../../lib/hooks/useMemberSession'
import { useBeforeUnload } from '../../lib/hooks/useBeforeUnload'
import { useAsync } from '../../lib/hooks/useAsync'
import { getMemberProfile, updateMemberProfile, uploadMemberPicture, clearMemberPicture } from '../../features/members/api'
import { memberStatusLabel, MEMBER_STATUS_CHIP } from '../../features/members/status'
import { getErrorMessage } from '../../lib/errors/ApiError'
import { usePageMeta } from '../../lib/utils/seo'
import { MemberPageHeader } from '../../components/member/MemberPageHeader'
import { MemberCard } from '../../components/member/MemberCard'
import { MemberAvatar } from '../../components/member/MemberAvatar'
import { FormField } from '../../components/form/FormField'
import { TextInput } from '../../components/form/TextInput'
import { Textarea } from '../../components/form/Textarea'
import { Select } from '../../components/form/Select'
import { FormActions } from '../../components/form/FormActions'
import { SaveButton } from '../../components/form/SaveButton'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import type { MemberProfileResponse, ProfileVisibility } from '../../types/member'

function formatList(values: string[]): string {
  return values.join(', ')
}

function parseList(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

interface ProfileForm {
  display_name: string
  bio: string
  skills: string
  interests: string
  github_url: string
  linkedin_url: string
  portfolio_url: string
  location: string
  timezone: string
  profile_visibility: ProfileVisibility
  picture_media_id: string | null
}

export default function MemberProfilePage() {
  usePageMeta({ title: 'Profile — Member portal — Thridha Labs' })

  const { member, refresh } = useMemberAuth()
  const { data, loading, error, reload } = useAsync(() => getMemberProfile(), [])
  useMemberSessionIssue(error)

  const [form, setForm] = useState<ProfileForm>({
    display_name: '',
    bio: '',
    skills: '',
    interests: '',
    github_url: '',
    linkedin_url: '',
    portfolio_url: '',
    location: '',
    timezone: '',
    profile_visibility: 'private',
    picture_media_id: null,
  })
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveNotice, setSaveNotice] = useState<string | null>(null)
  const [pictureBusy, setPictureBusy] = useState(false)
  const [pictureError, setPictureError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  useBeforeUnload(dirty)

  const hydrated = useRef(false)
  useEffect(() => {
    if (!data || hydrated.current) return
    hydrated.current = true
    setForm({
      display_name: data.profile.display_name ?? '',
      bio: data.profile.bio ?? '',
      skills: formatList(data.profile.skills),
      interests: formatList(data.profile.interests),
      github_url: data.profile.github_url ?? '',
      linkedin_url: data.profile.linkedin_url ?? '',
      portfolio_url: data.profile.portfolio_url ?? '',
      location: data.profile.location ?? '',
      timezone: data.profile.timezone ?? '',
      profile_visibility: data.profile.profile_visibility,
      picture_media_id: data.profile.picture_media_id,
    })
    setDirty(false)
  }, [data])

  function patch(p: Partial<ProfileForm>): void {
    setForm((prev) => ({ ...prev, ...p }))
    setDirty(true)
    setSaveNotice(null)
  }

  async function handlePictureChange(event: React.ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setPictureBusy(true)
    setPictureError(null)
    try {
      await uploadMemberPicture(file)
      hydrated.current = false
      await reload()
    } catch (caught) {
      setPictureError(getErrorMessage(caught, 'Could not upload the picture.'))
    } finally {
      setPictureBusy(false)
    }
  }

  async function handlePictureRemove(): Promise<void> {
    setPictureBusy(true)
    setPictureError(null)
    try {
      await clearMemberPicture()
      hydrated.current = false
      await reload()
    } catch (caught) {
      setPictureError(getErrorMessage(caught, 'Could not remove the picture.'))
    } finally {
      setPictureBusy(false)
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    const skills = parseList(form.skills)
    const interests = parseList(form.interests)
    if (!form.bio.trim() || skills.length === 0 || interests.length === 0) {
      setSaveError('Bio, skills and interests are required to complete your profile.')
      return
    }

    setSaving(true)
    setSaveError(null)
    setSaveNotice(null)
    try {
      await updateMemberProfile({
        display_name: form.display_name.trim() || null,
        bio: form.bio.trim(),
        skills,
        interests,
        github_url: form.github_url.trim() || null,
        linkedin_url: form.linkedin_url.trim() || null,
        portfolio_url: form.portfolio_url.trim() || null,
        location: form.location.trim() || null,
        timezone: form.timezone.trim() || null,
        profile_visibility: form.profile_visibility,
      })
      setDirty(false)
      setSaveNotice('Profile saved.')
      hydrated.current = false
      await Promise.all([reload(), refresh()])
    } catch (caught) {
      setSaveError(getErrorMessage(caught, 'Could not save your profile.'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <ContentSkeleton rows={5} />
  }

  if (error) {
    return <ErrorState error={error} onRetry={reload} />
  }

  const profile = data as MemberProfileResponse | undefined
  const displayName = profile?.full_name || member?.full_name || 'Member'
  const status = profile?.status ?? member?.status

  return (
    <div className="member-page">
      <MemberPageHeader
        title="My Profile"
        description={
          profile?.profile_complete
            ? 'Keep your public details up to date.'
            : 'Complete your bio, skills and interests to finish your profile.'
        }
      />

      <div className="member-stack member-form">
        <MemberCard>
          <div className="member-profile-hero">
            <MemberAvatar name={displayName} mediaId={form.picture_media_id} size="xl" accent />
            <div className="member-profile-hero__meta">
              <h2 className="member-profile-hero__name">{displayName}</h2>
              <div className="member-profile-hero__sub">
                <span>{profile?.role_label ?? 'Lab member'}</span>
                {profile?.member_id ? <span className="mono">{profile.member_id}</span> : null}
                {status ? (
                  <span className={`chip ${MEMBER_STATUS_CHIP[status]}`}>
                    {memberStatusLabel(status)}
                  </span>
                ) : null}
                {profile?.created_at ? <span>Joined {formatDate(profile.created_at)}</span> : null}
              </div>
              <div className="member-picture__actions">
                <input
                  ref={fileRef}
                  id="member-picture"
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  className="visually-hidden"
                  onChange={(event) => void handlePictureChange(event)}
                />
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  disabled={pictureBusy}
                  onClick={() => fileRef.current?.click()}
                >
                  {pictureBusy ? 'Working…' : form.picture_media_id ? 'Replace picture' : 'Upload picture'}
                </button>
                {form.picture_media_id ? (
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    disabled={pictureBusy}
                    onClick={() => void handlePictureRemove()}
                  >
                    Remove
                  </button>
                ) : null}
              </div>
              {pictureError ? (
                <p className="form-field__error" role="alert">
                  {pictureError}
                </p>
              ) : null}
            </div>
          </div>
        </MemberCard>

        <form className="member-stack member-form" onSubmit={handleSubmit} noValidate>
          <MemberCard title="Details">
            <FormField id="member-display-name" label="Display name">
              <TextInput
                id="member-display-name"
                value={form.display_name}
                onChange={(value) => patch({ display_name: value })}
                placeholder="How your name shows up"
              />
            </FormField>
            <FormField id="member-bio" label="Bio" hint="Required" required>
              <Textarea
                id="member-bio"
                rows={4}
                value={form.bio}
                onChange={(value) => patch({ bio: value })}
                placeholder="A short introduction"
              />
            </FormField>
            <FormField id="member-skills" label="Skills" hint="Comma-separated, required" required>
              <TextInput
                id="member-skills"
                value={form.skills}
                onChange={(value) => patch({ skills: value })}
                placeholder="Python, React, CAD"
              />
            </FormField>
            <FormField id="member-interests" label="Interests" hint="Comma-separated, required" required>
              <TextInput
                id="member-interests"
                value={form.interests}
                onChange={(value) => patch({ interests: value })}
                placeholder="Robotics, Sustainability"
              />
            </FormField>
            <FormField id="member-location" label="Location">
              <TextInput
                id="member-location"
                value={form.location}
                onChange={(value) => patch({ location: value })}
                placeholder="City, Country"
              />
            </FormField>
            <FormField id="member-timezone" label="Timezone" hint="IANA name, e.g. Asia/Kolkata">
              <TextInput
                id="member-timezone"
                value={form.timezone}
                onChange={(value) => patch({ timezone: value })}
                placeholder="UTC"
              />
            </FormField>
            <FormField
              id="member-visibility"
              label="Profile visibility"
              hint="Controls whether your public profile and public works are visible"
            >
              <Select
                id="member-visibility"
                value={form.profile_visibility}
                options={[
                  { value: 'private', label: 'Private — only you' },
                  { value: 'members', label: 'Members — signed-in lab members' },
                  { value: 'public', label: 'Public — anyone with the link' },
                ]}
                onChange={(value) => patch({ profile_visibility: value as ProfileVisibility })}
              />
            </FormField>
          </MemberCard>

          <MemberCard title="Links">
            <FormField id="member-github" label="GitHub">
              <TextInput
                id="member-github"
                type="url"
                value={form.github_url}
                onChange={(value) => patch({ github_url: value })}
                placeholder="https://github.com/you"
              />
            </FormField>
            <FormField id="member-linkedin" label="LinkedIn">
              <TextInput
                id="member-linkedin"
                type="url"
                value={form.linkedin_url}
                onChange={(value) => patch({ linkedin_url: value })}
                placeholder="https://linkedin.com/in/you"
              />
            </FormField>
            <FormField id="member-portfolio" label="Portfolio">
              <TextInput
                id="member-portfolio"
                type="url"
                value={form.portfolio_url}
                onChange={(value) => patch({ portfolio_url: value })}
                placeholder="https://you.example.com"
              />
            </FormField>
          </MemberCard>

          {saveError ? (
            <p className="form-field__error form-field__error--form" role="alert">
              {saveError}
            </p>
          ) : null}
          {saveNotice ? (
            <p className="admin-form__dirty" role="status">
              {saveNotice}
            </p>
          ) : null}
          {dirty ? (
            <p className="admin-form__dirty" role="status">
              Unsaved changes.
            </p>
          ) : null}

          <FormActions>
            <SaveButton busy={saving}>Save profile</SaveButton>
          </FormActions>
        </form>
      </div>
    </div>
  )
}
