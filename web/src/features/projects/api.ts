/** Projects feature API module — public listing/detail + future admin CRUD. */

import { api } from '../../lib/api/client'
import type { StatusResponse } from '../../types/api'
import type { AdminProject, Paginated, ProjectQuery, PublicProject } from '../../types'

export function getPublicProjects(query: ProjectQuery = {}): Promise<Paginated<PublicProject>> {
  return api.get<Paginated<PublicProject>>('/public/projects', { query })
}

export function getPublicProject(slug: string): Promise<PublicProject> {
  return api.get<PublicProject>(`/public/projects/${slug}`)
}

export function listProjects(query: ProjectQuery = {}): Promise<Paginated<AdminProject>> {
  return api.get<Paginated<AdminProject>>('/projects', { query })
}

export function getProject(projectId: string): Promise<AdminProject> {
  return api.get<AdminProject>(`/projects/${projectId}`)
}

export function createProject(payload: unknown): Promise<AdminProject> {
  return api.post<AdminProject>('/projects', payload)
}

export function updateProject(projectId: string, payload: unknown): Promise<AdminProject> {
  return api.patch<AdminProject>(`/projects/${projectId}`, payload)
}

export function deleteProject(projectId: string): Promise<StatusResponse> {
  return api.delete<StatusResponse>(`/projects/${projectId}`)
}