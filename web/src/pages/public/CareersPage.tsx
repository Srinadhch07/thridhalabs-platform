/**
 * Careers page — open roles at the lab plus the careers intro from settings.
 *
 * When the owner has not enabled careers, the page falls back to the standard
 * 404 treatment (same idea as the maintenance gate): the API reveals nothing,
 * navigation hides the link, and the route itself refuses to exist.
 */

import { useCareers } from '../../app/providers/CareersProvider'
import { OpportunityCard } from '../../components/public/OpportunityCard'
import { PageHeader } from '../../components/public/PageHeader'
import { Reveal } from '../../components/public/Reveal'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { usePublicOpportunities } from '../../features/careers/hooks'
import { absolutePageUrl, useBrandingOgImage, usePageMeta } from '../../lib/utils/seo'
import NotFoundPage from './NotFoundPage'

export default function CareersPage() {
  const careers = useCareers()
  const brandingOgImage = useBrandingOgImage()
  const enabled = careers.enabled

  usePageMeta({
    title: 'Careers — Thridha Labs',
    description: 'Open roles and ways to work with Thridha Labs.',
    canonical: absolutePageUrl('/careers'),
    ogImage: brandingOgImage,
  })

  const { data, loading, error, reload } = usePublicOpportunities(
    { sort: 'display_order', order: 'asc' },
    !enabled,
  )

  if (!enabled) {
    return <NotFoundPage />
  }

  if (loading) {
    return <ContentSkeleton rows={4} />
  }

  if (error) {
    return <ErrorState title="Unable to load roles" error={error} onRetry={reload} />
  }

  const opportunities = data?.items ?? []
  const heading = careers.data?.heading || 'Open roles at the lab'
  const lede = careers.data?.description || undefined

  return (
    <>
      <PageHeader eyebrow="Careers / open" title={heading} lede={lede} />
      <div className="shell" style={{ paddingBlock: 'var(--space-7)' }}>
        {opportunities.length === 0 ? (
          <EmptyState
            title="No open roles right now"
            description="There is nothing open at the moment — check back soon."
          />
        ) : (
          <div className="opportunity-list">
            {opportunities.map((opportunity) => (
              <Reveal key={opportunity.slug}>
                <OpportunityCard
                  opportunity={opportunity}
                  applicationTemplate={careers.data?.application_template ?? null}
                />
              </Reveal>
            ))}
          </div>
        )}
      </div>
    </>
  )
}