/** Admin account types (Phase 2 `/auth` API). */

export type AdminRole = 'owner' | 'admin' | 'editor'

export interface Me {
  id: string
  email: string
  role: AdminRole
  is_active: boolean
}