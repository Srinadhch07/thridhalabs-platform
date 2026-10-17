/** Clients hooks. */

import { useAsync } from '../../lib/hooks/useAsync'
import { getClient, getPublicClient, getPublicClients, listClients } from './api'
import type { ClientQuery } from '../../types/content'

export function usePublicClients(query: ClientQuery = {}) {
  return useAsync(() => getPublicClients(query), [JSON.stringify(query)])
}

export function usePublicClient(slug: string | undefined) {
  return useAsync(
    async () => {
      if (!slug) throw new Error('Missing client slug')
      return getPublicClient(slug)
    },
    [slug],
  )
}

export function useAdminClients(query: ClientQuery = {}) {
  return useAsync(() => listClients(query), [JSON.stringify(query)])
}

export function useAdminClient(clientId: string | undefined) {
  return useAsync(
    async () => {
      if (!clientId) throw new Error('Missing client id')
      return getClient(clientId)
    },
    [clientId],
  )
}