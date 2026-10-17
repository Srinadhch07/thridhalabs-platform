/** Member status display helpers shared by the portal and the admin panel. */

import type { MemberStatus } from '../../types/member'

export const MEMBER_STATUS_LABELS: Record<MemberStatus, string> = {
  pending_setup: 'Pending setup',
  active: 'Active',
  inactive: 'Inactive',
}

export const MEMBER_STATUS_CHIP: Record<MemberStatus, string> = {
  pending_setup: 'chip--warn',
  active: 'chip--ok',
  inactive: 'chip--muted',
}

export function memberStatusLabel(status: MemberStatus): string {
  return MEMBER_STATUS_LABELS[status] ?? status
}