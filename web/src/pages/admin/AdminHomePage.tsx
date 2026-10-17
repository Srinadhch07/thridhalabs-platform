/**
 * Admin dashboard — operational overview driven entirely by the existing admin
 * list endpoints (counts) plus quick actions into the control center.
 */

import { Link } from 'react-router-dom'
import { useAdminSessionIssue } from '../../lib/hooks/useAdminSession'
import { usePageMeta } from '../../lib/utils/seo'
import { useAdminBranding } from '../../features/branding/hooks'
import { useAdminClients } from '../../features/clients/hooks'
import { useMediaList } from '../../features/media/hooks'
import { useAdminProjects } from '../../features/projects/hooks'
import { useAdminSettings } from '../../features/settings/hooks'
import { useAdminTestimonials } from '../../features/testimonials/hooks'
import { PageHeader } from '../../components/admin/PageHeader'
import { ContentSkeleton } from '../../components/ui/ContentSkeleton'

interface Metric {
  label: string
  count: number
  to: string
}

export default function AdminHomePage() {
  usePageMeta({ title: 'Dashboard — Admin — Thridha Labs' })

  const clients = useAdminClients({ page: 1, page_size: 1 })
  const projects = useAdminProjects({ page: 1, page_size: 1 })
  const testimonials = useAdminTestimonials({ page: 1, page_size: 1 })
  const media = useMediaList({ page: 1, page_size: 1 })
  const settings = useAdminSettings()
  const branding = useAdminBranding()

  useAdminSessionIssue(clients.error)
  useAdminSessionIssue(projects.error)
  useAdminSessionIssue(testimonials.error)
  useAdminSessionIssue(media.error)
  useAdminSessionIssue(settings.error)
  useAdminSessionIssue(branding.error)

  const loading = clients.loading || projects.loading || testimonials.loading || media.loading

  const metrics: Metric[] = [
    { label: 'Clients', count: clients.data?.total ?? 0, to: '/admin/clients' },
    { label: 'Projects', count: projects.data?.total ?? 0, to: '/admin/projects' },
    { label: 'Testimonials', count: testimonials.data?.total ?? 0, to: '/admin/testimonials' },
    { label: 'Media assets', count: media.data?.total ?? 0, to: '/admin/media' },
  ]

  return (
    <div>
      <PageHeader
        eyebrow="Control center"
        title="Dashboard"
        description="Everything on the public site is managed from here."
      />

      {loading ? (
        <ContentSkeleton rows={3} />
      ) : (
        <section className="admin-metrics" aria-label="Site overview">
          {metrics.map((metric) => (
            <Link key={metric.label} to={metric.to} className="admin-metric">
              <span className="admin-metric__label">{metric.label}</span>
              <span className="admin-metric__count">{metric.count}</span>
            </Link>
          ))}
        </section>
      )}

      <section className="admin-quick-actions">
        <h2 style={{ fontSize: 'var(--fs-md)' }}>Quick actions</h2>
        <div className="admin-quick-actions__grid">
          <Link className="btn btn--ghost" to="/admin/projects/new">
            Add project
          </Link>
          <Link className="btn btn--ghost" to="/admin/clients/new">
            Add client
          </Link>
          <Link className="btn btn--ghost" to="/admin/testimonials/new">
            Add testimonial
          </Link>
          <Link className="btn btn--ghost" to="/admin/media">
            Upload media
          </Link>
          <Link className="btn btn--ghost" to="/admin/settings">
            Edit settings
          </Link>
          <Link className="btn btn--ghost" to="/admin/branding">
            Edit branding
          </Link>
        </div>
      </section>
    </div>
  )
}