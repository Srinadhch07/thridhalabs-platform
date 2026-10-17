/**
 * Admin account — the signed-in session (email, role, active state) and
 * sign-out. Password management is deliberately out of scope; the session is
 * HttpOnly-cookie based and role information comes from the backend.
 */

import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../app/providers/AuthProvider'
import { ROLE_LABELS } from '../../features/auth/rbac'
import { usePageMeta } from '../../lib/utils/seo'
import { PageHeader } from '../../components/admin/PageHeader'

export default function AdminAccountPage() {
  usePageMeta({ title: 'Account — Admin — Thridha Labs' })
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  async function handleSignOut(): Promise<void> {
    await signOut()
    navigate('/admin/login', { replace: true })
  }

  return (
    <div>
      <PageHeader eyebrow="Profile" title="Account" description="Your signed-in session." />

      <div className="card account-card" style={{ maxWidth: '520px' }}>
        <dl className="account-list">
          <div className="account-list__row">
            <dt>Email</dt>
            <dd>{user?.email}</dd>
          </div>
          <div className="account-list__row">
            <dt>Role</dt>
            <dd>
              <span className={`chip chip--role chip--${user?.role ?? 'editor'}`}>
                {user ? ROLE_LABELS[user.role] : ''}
              </span>
            </dd>
          </div>
          <div className="account-list__row">
            <dt>Status</dt>
            <dd>
              {user?.is_active ? (
                <span className="chip chip--ok">Active</span>
              ) : (
                <span className="chip chip--muted">Disabled</span>
              )}
            </dd>
          </div>
        </dl>

        <p className="admin-section__hint">
          Role privileges are enforced by the backend. Editors manage content; admins and
          owners also delete content and media. Password changes and account management are
          not part of this control center.
        </p>

        <div>
          <button type="button" className="btn btn--ghost" onClick={() => void handleSignOut()}>
            Sign out
          </button>
        </div>
      </div>
    </div>
  )
}