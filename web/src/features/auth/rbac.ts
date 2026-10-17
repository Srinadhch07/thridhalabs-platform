/** Role privileges (frontend UX mirror of the backend ROLE_RANK hierarchy). */

import type { AdminRole } from '../../types/admin'

export const ROLE_RANK: Record<AdminRole, number> = {
  editor: 1,
  admin: 2,
  owner: 3,
}

export const ROLE_LABELS: Record<AdminRole, string> = {
  owner: 'Owner',
  admin: 'Admin',
  editor: 'Editor',
}

/** Higher rank === more privilege. The backend remains authoritative. */
export function roleRank(role: AdminRole): number {
  return ROLE_RANK[role]
}

/** Whether a role meets (or exceeds) the required privilege rank. */
export function can(role: AdminRole | undefined, required: AdminRole): boolean {
  if (!role) return false
  return ROLE_RANK[role] >= ROLE_RANK[required]
}

/**
 * Content deletion requires at least `admin` in the backend
 * (`require_role("admin")`), so editors must not see delete actions.
 */
export function canDelete(role: AdminRole | undefined): boolean {
  return can(role, 'admin')
}