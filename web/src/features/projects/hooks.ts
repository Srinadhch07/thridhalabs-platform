/** Projects hooks. */

import { useAsync } from '../../lib/hooks/useAsync'
import { getProject, getPublicProject, getPublicProjects, listProjects } from './api'
import type { ProjectQuery } from '../../types/content'

export function usePublicProjects(query: ProjectQuery = {}) {
  return useAsync(() => getPublicProjects(query), [JSON.stringify(query)])
}

export function usePublicProject(slug: string | undefined) {
  return useAsync(
    async () => {
      if (!slug) throw new Error('Missing project slug')
      return getPublicProject(slug)
    },
    [slug],
  )
}

export function useAdminProjects(query: ProjectQuery = {}) {
  return useAsync(() => listProjects(query), [JSON.stringify(query)])
}

export function useAdminProject(projectId: string | undefined) {
  return useAsync(
    async () => {
      if (!projectId) throw new Error('Missing project id')
      return getProject(projectId)
    },
    [projectId],
  )
}