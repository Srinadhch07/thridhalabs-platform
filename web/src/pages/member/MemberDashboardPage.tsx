/**
 * Member overview — landing page of the portal.
 *
 * Reads the session identity from the member auth context and enriches it with
 * the member's own profile (avatar, role, completion) when available. The
 * profile request is a nicety, not a requirement: if it fails the page still
 * renders the identity it already has from the session.
 */

import { Link } from 'react-router-dom'
import { useMemberAuth } from '../../app/providers/MemberAuthProvider'
import { useAsync } from '../../lib/hooks/useAsync'
import { useMemberSessionIssue } from '../../lib/hooks/useMemberSession'
import { getMemberProfile } from '../../features/members/api'
import { memberStatusLabel, MEMBER_STATUS_CHIP } from '../../features/members/status'
import { usePageMeta } from '../../lib/utils/seo'
import { MemberPageHeader } from '../../components/member/MemberPageHeader'
import { MemberCard } from '../../components/member/MemberCard'
import { MemberAvatar } from '../../components/member/MemberAvatar'

function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

export default function MemberDashboardPage() {
  usePageMeta({ title: 'Member portal — Thridha Labs' })

  const { member } = useMemberAuth()
  const { data: profile, error: profileError } = useAsync(() => getMemberProfile(), [])
  useMemberSessionIssue(profileError)

  if (!member) return null

  const displayName = profile?.profile.display_name || member.full_name || 'Member'
  const roleLabel = profile?.role_label
  const pictureId = profile?.profile.picture_media_id ?? null
  const profileComplete = profile?.profile_complete ?? member.profile_complete

  const skills = profile?.profile.skills ?? []
  const interests = profile?.profile.interests ?? []
  const missing: string[] = []
  if (profile) {
    if (!profile.profile.bio) missing.push('A short bio')
    if (profile.profile.skills.length === 0) missing.push('At least one skill')
    if (profile.profile.interests.length === 0) missing.push('At least one interest')
  }

  return (
    <div className="member-page">
      <MemberPageHeader
        title={member.full_name ? `Welcome back, ${member.full_name}` : 'Welcome back'}
        description="Your lab membership at a glance."
        actions={
          <Link className="btn btn--ghost" to="/member/profile">
            {profileComplete ? 'Edit profile' : 'Complete profile'}
          </Link>
        }
      />

      <div className="member-grid member-grid--2">
        <MemberCard>
          <div className="member-profile-head">
            <MemberAvatar name={displayName} mediaId={pictureId} size="lg" accent />
            <div className="member-profile-head__meta">
              <h2 className="member-profile-head__name">{displayName}</h2>
              <span className="member-profile-head__sub">
                {roleLabel ?? 'Lab member'} · <span className="mono">{member.member_id}</span>
              </span>
              <span className={`chip ${MEMBER_STATUS_CHIP[member.status]}`}>
                {memberStatusLabel(member.status)}
              </span>
            </div>
          </div>
          <hr className="member-divider" />
          <dl className="member-meta">
            <div className="member-meta__row">
              <dt>Email</dt>
              <dd>{member.email}</dd>
            </div>
            <div className="member-meta__row">
              <dt>Last sign-in</dt>
              <dd>{formatDate(member.last_login_at)}</dd>
            </div>
          </dl>
        </MemberCard>

        <MemberCard
          title={profileComplete ? 'Profile' : 'Finish your profile'}
          className={profileComplete ? undefined : 'member-completion'}
          action={
            <Link className="btn btn--ghost btn--sm" to="/member/profile">
              {profileComplete ? 'Edit' : 'Continue'}
            </Link>
          }
        >
          {profileComplete ? (
            <div className="member-stack" style={{ gap: 'var(--space-3)' }}>
              <p className="member-card__desc" style={{ color: 'var(--color-secondary)' }}>
                Your profile is complete. Members and the lab team can see your details.
              </p>
              {skills.length > 0 ? (
                <div className="member-field">
                  <span className="member-field__label">Skills</span>
                  <ul className="member-tags">
                    {skills.map((skill) => (
                      <li key={skill} className="member-tag">
                        {skill}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {interests.length > 0 ? (
                <div className="member-field">
                  <span className="member-field__label">Interests</span>
                  <ul className="member-tags">
                    {interests.map((interest) => (
                      <li key={interest} className="member-tag">
                        {interest}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ) : (
            <div className="member-stack" style={{ gap: 'var(--space-3)' }}>
              <p className="member-card__desc">
                Add a few details so the lab team knows who you are and what you work on.
              </p>
              {missing.length > 0 ? (
                <ul className="member-completion__list">
                  {missing.map((item) => (
                    <li key={item}>
                      <span aria-hidden="true">•</span>
                      {item}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          )}
        </MemberCard>
      </div>
    </div>
  )
}
