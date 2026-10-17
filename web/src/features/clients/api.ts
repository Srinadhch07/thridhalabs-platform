/** Clients feature API module — public listing/detail + future admin CRUD. */

import { api } from '../../lib/api/client'
import type { StatusResponse } from '../../types/api'
import type { AdminClient, ClientQuery, Paginated, PublicClient } from '../../types'

export function getPublicClients(query: ClientQuery = {}): Promise<Paginated<PublicClient>> {
  return api.get<Paginated<PublicClient>>('/public/clients', { query })
}

export function getPublicClient(slug: string): Promise<PublicClient> {
  return api.get<PublicClient>(`/public/clients/${slug}`)
}

export function listClients(query: ClientQuery = {}): Promise<Paginated<AdminClient>> {
  return api.get<Paginated<AdminClient>>('/clients', { query })
}

export function getClient(clientId: string): Promise<AdminClient> {
  return api.get<AdminClient>(`/clients/${clientId}`)
}

export function createClient(payload: unknown): Promise<AdminClient> {
  return api.post<AdminClient>('/clients', payload)
}

export function updateClient(clientId: string, payload: unknown): Promise<AdminClient> {
  return api.patch<AdminClient>(`/clients/${clientId}`, payload)
}

export function deleteClient(clientId: string): Promise<StatusResponse> {
  return api.delete<StatusResponse>(`/clients/${clientId}`)
}