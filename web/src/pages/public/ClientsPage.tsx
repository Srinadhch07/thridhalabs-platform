/**
 * Clients page — the people and organisations Thridha Labs works with,
 * straight from the public clients API.
 */

import { ClientTile } from '../../components/public/ClientTile'
import { PageHeader } from '../../components/public/PageHeader'
import { Reveal } from '../../components/public/Reveal'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { usePublicClients } from '../../features/clients/hooks'
import { absolutePageUrl, useBrandingOgImage, usePageMeta } from '../../lib/utils/seo'

export default function ClientsPage() {
  const { data, loading, error, reload } = usePublicClients({ sort: 'display_order', order: 'asc' })
  const brandingOgImage = useBrandingOgImage()

  usePageMeta({
    title: 'Clients — Thridha Labs',
    description:
      'The people and teams Thridha Labs builds with — real collaborations, recorded honestly.',
    canonical: absolutePageUrl('/clients'),
    ogImage: brandingOgImage,
  })

  const clients = data?.items ?? []

  return (
    <>
      <PageHeader
        eyebrow="Clients / index"
        title="People we work with"
        lede="The teams and organisations we build with. Every entry is a real collaboration from the lab archive."
        meta={
          <p className="eyebrow" style={{ marginBottom: 0 }}>
            {data ? `${clients.length.toString().padStart(2, '0')} entries on file` : 'Indexing…'}
          </p>
        }
      />

      <div className="shell" style={{ paddingBlock: 'var(--space-7)' }}>
        {loading ? (
          <ContentSkeleton rows={6} />
        ) : error ? (
          <ErrorState title="Unable to load clients" error={error} onRetry={reload} />
        ) : clients.length === 0 ? (
          <EmptyState title="No clients yet" description="Clients will appear here when added." />
        ) : (
          <div className="client-grid">
            {clients.map((client) => (
              <Reveal key={client.slug} className="reveal--grid">
                <ClientTile client={client} />
              </Reveal>
            ))}
          </div>
        )}
      </div>
    </>
  )
}