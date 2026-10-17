/**
 * Home page — the public Thridha Labs landing, built as an "experimental
 * technology unit" rather than a generic agency page.
 *
 * Sections: hero → intro → selected work → clients → experiments/technology →
 * testimonials → philosophy → CTA. Every data-driven section degrades
 * gracefully: API errors render a section-level retry, and empty content hides
 * the section entirely — no fabricated metrics or claims.
 */

import { Link } from 'react-router-dom'
import { useSiteSettings } from '../../app/providers/SiteSettingsProvider'
import { ClientTile } from '../../components/public/ClientTile'
import { ActivityCarousel } from '../../components/public/ActivityCarousel'
import { ProjectCard } from '../../components/public/ProjectCard'
import { Reveal } from '../../components/public/Reveal'
import { SectionHeader } from '../../components/public/SectionHeader'
import { TechChips } from '../../components/public/TechChips'
import { TestimonialCard } from '../../components/public/TestimonialCard'
import { ErrorState } from '../../components/ui/ErrorState'
import { usePublicClients } from '../../features/clients/hooks'
import { usePublicProjects } from '../../features/projects/hooks'
import { usePublicTestimonials } from '../../features/testimonials/hooks'
import { usePageMeta, useBrandingOgImage, absolutePageUrl } from '../../lib/utils/seo'
import { useJsonLd } from '../../lib/hooks/useJsonLd'
import type { PublicClient, PublicProject, PublicTestimonial } from '../../types/content'

const PHILOSOPHY_WORDS: Array<{ word: string; ghost?: boolean }> = [
  { word: 'Build' },
  { word: 'Break', ghost: true },
  { word: 'Learn' },
  { word: 'Repeat', ghost: true },
]

function isThridhaBrand(siteName: string): boolean {
  return /^thridha labs$/i.test(siteName)
}

/* ------------------------------------------------------------------ */
/* Hero                                                                */
/* ------------------------------------------------------------------ */

function HeroSection({
  siteName,
  tagline,
  description,
}: {
  siteName: string
  tagline: string
  description: string
}) {
  const title = isThridhaBrand(siteName) ? (
    <>
      <span className="wordmark__line">
        <span>Thridha </span>
      </span>
      <span className="wordmark__line">
        <span className="wordmark--ghost">Labs</span>
        <i className="wordmark__rule" aria-hidden="true" />
      </span>
    </>
  ) : (
    siteName
  )

  return (
    <section className="hero" aria-labelledby="hero-title">
      <p className="hero-legend hero-legend--top">
        <span className="hud-dot" aria-hidden="true" /> Core / online
      </p>

      <div className="hero-orbit" aria-hidden="true">
        <span className="orbit-ring orbit-ring--outer" />
        <span className="orbit-ring orbit-ring--mid" />
        <span className="orbit-ring orbit-ring--inner" />
        <span className="orbit-core" />
        <span className="orbit-node" style={{ top: '16%', left: '60%' }} />
        <span className="orbit-node" style={{ top: '70%', left: '24%' }} />
      </div>

      <div className="shell hero__inner">
        <p className="eyebrow hero-eyebrow">
          <span className="rec-dot" aria-hidden="true" />
          Thridha Labs — experimental technology unit
        </p>
        <h1 id="hero-title" className="wordmark" aria-label={siteName}>
          {title}
        </h1>
        <p className="hero__statement">
          {tagline}
          <span className="caret" aria-hidden="true" />
        </p>
        <p className="hero__support">{description}</p>
        <div className="cta-row">
          <Link className="btn btn--primary" to="/projects">
            Explore the lab
          </Link>
          <Link className="btn btn--ghost" to="/projects?type=experiment">
            See experiments
          </Link>
        </div>
      </div>

      <p className="hero-legend hero-legend--side" aria-hidden="true">
        Lab
      </p>
      <p className="hero-scroll-hint">Scroll / explore</p>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/* Intro                                                               */
/* ------------------------------------------------------------------ */

function IntroSection({ siteName, description }: { siteName: string; description: string }) {
  return (
    <section className="section" aria-labelledby="intro-title">
      <div className="shell intro-grid">
        <Reveal>
          <p className="tag section-head__tag">
            <span className="hud-dot" aria-hidden="true" /> Ideas
          </p>
          <h2 id="intro-title" className="section-head__title">
            Ideas connect. Experiments begin.
          </h2>
        </Reveal>
        <Reveal delay={120} className="intro-copy">
          <p>
            <strong>{siteName}</strong> is a technology and AI experimentation lab. {description}
          </p>
          <p>No ceremony, no roadmap theatre — just the loop, run honestly.</p>
          <ul className="mode-list">
            <li className="mode-item">
              <span className="mode-item__index">01</span>
              <span className="mode-item__name">Research</span>
              <span className="mode-item__desc">What's next</span>
            </li>
            <li className="mode-item">
              <span className="mode-item__index">02</span>
              <span className="mode-item__name">Build</span>
              <span className="mode-item__desc">How it works</span>
            </li>
            <li className="mode-item">
              <span className="mode-item__index">03</span>
              <span className="mode-item__name">Ship</span>
              <span className="mode-item__desc">What you get</span>
            </li>
          </ul>
        </Reveal>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/* Selected work                                                       */
/* ------------------------------------------------------------------ */

function SelectedWorkSection({
  projects,
  error,
  reload,
}: {
  projects: PublicProject[]
  error: Error | null
  reload: () => void
}) {
  if (error) {
    return (
      <section className="section">
        <div className="shell">
          <SectionHeader tag="Selected work" title="Selected work." />
          <ErrorState title="Unable to load projects" error={error} onRetry={reload} />
        </div>
      </section>
    )
  }
  if (projects.length === 0) return null

  const [heroProject, ...rest] = projects
  return (
      <section className="section" aria-labelledby="selected-title">
      <div className="shell">
        <SectionHeader
          id="selected-title"
          tag="Selected work"
          title="Running, not promised."
          action={{ to: '/projects', label: 'All projects' }}
        />
        <div className="project-grid">
          <Reveal className="reveal--grid">
            <ProjectCard featured project={heroProject} />
          </Reveal>
          {rest.map((project) => (
            <Reveal key={project.slug} className="reveal--grid">
              <ProjectCard project={project} />
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/* Clients strip                                                       */
/* ------------------------------------------------------------------ */

function ClientsSection({
  clients,
  error,
  reload,
}: {
  clients: PublicClient[]
  error: Error | null
  reload: () => void
}) {
  if (error) {
    return (
      <section className="section">
        <div className="shell">
          <SectionHeader tag="Collaborators" title="People we build with" />
          <ErrorState title="Unable to load clients" error={error} onRetry={reload} />
        </div>
      </section>
    )
  }
  if (clients.length === 0) return null

  const featured = clients.filter((client) => client.featured)
  const strip = (featured.length > 0 ? featured : clients).slice(0, 6)
  return (
      <section className="section" aria-labelledby="clients-title">
      <div className="shell">
        <SectionHeader
          id="clients-title"
          tag="Collaborators"
          title="People we build with."
          action={{ to: '/clients', label: 'All clients' }}
        />
        <div className="client-grid">
          {strip.map((client) => (
            <Reveal key={client.slug} className="reveal--grid">
              <ClientTile client={client} />
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/* Experiments + technology                                            */
/* ------------------------------------------------------------------ */

function ExperimentsSection({
  projects,
  excluded,
}: {
  projects: PublicProject[]
  excluded: Set<string>
}) {
  if (projects.length === 0) return null

  const experiments = projects.filter(
    (project) => project.project_type === 'experiment' && !excluded.has(project.slug),
  )
  const technologies = [...new Set(projects.flatMap((project) => project.technologies))].slice(0, 18)
  if (experiments.length === 0 && technologies.length === 0) return null

  return (
      <section className="section" aria-labelledby="experiments-title">
      <div className="shell">
        <SectionHeader
          id="experiments-title"
          tag="Experiments"
          title="Experiments, live in the lab."
          action={{ to: '/projects?type=experiment', label: 'All experiments' }}
        />
        {experiments.length > 0 && (
          <div className="project-grid">
            {experiments.map((project) => (
              <Reveal key={project.slug} className="reveal--grid">
                <ProjectCard project={project} />
              </Reveal>
            ))}
          </div>
        )}
        {technologies.length > 0 && (
          <Reveal delay={140}>
            <p className="eyebrow experiments__tech">
              Technology in use
            </p>
            <TechChips items={technologies} />
          </Reveal>
        )}
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/* Testimonials                                                        */
/* ------------------------------------------------------------------ */

function TestimonialsSection({
  items,
  error,
  reload,
}: {
  items: PublicTestimonial[]
  error: Error | null
  reload: () => void
}) {
  if (error) {
    return (
      <section className="section">
        <div className="shell">
          <SectionHeader tag="Signal" title="What people say." />
          <ErrorState title="Unable to load testimonials" error={error} onRetry={reload} />
        </div>
      </section>
    )
  }
  if (items.length === 0) return null

  const featured = items.filter((item) => item.featured)
  const strip = (featured.length > 0 ? featured : items).slice(0, 3)
  return (
      <section className="section" aria-labelledby="testimonials-title">
      <div className="shell">
        <SectionHeader
          id="testimonials-title"
          tag="Signal"
          title="What people say."
          action={{ to: '/testimonials', label: 'All testimonials' }}
        />
        <div className="quote-grid">
          {strip.map((item) => (
            <Reveal key={item.id} className="reveal--grid">
              <TestimonialCard item={item} />
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/* Philosophy + CTA                                                    */
/* ------------------------------------------------------------------ */

function PhilosophySection({ siteName }: { siteName: string }) {
  return (
      <section className="section" aria-labelledby="philosophy-title">
      <div className="shell">
        <p className="tag section-head__tag">
          <span className="hud-dot" aria-hidden="true" /> The loop
        </p>
        <h2 id="philosophy-title" className="visually-hidden">
          How we operate
        </h2>
        <ul className="philosophy-list">
          {PHILOSOPHY_WORDS.map((entry, index) => (
            <li key={entry.word}>
              <Reveal delay={index * 90}>
                <span className={`philosophy-word${entry.ghost ? ' philosophy-word--ghost' : ''}`}>
                  {entry.word}
                </span>
              </Reveal>
            </li>
          ))}
        </ul>
        <Reveal delay={380}>
          <p className="philosophy-foot">
            That is how we build at <b>{siteName}</b>. No ceremony, no roadmap theatre — just the
            loop, run honestly.
          </p>
        </Reveal>
      </div>
    </section>
  )
}

function CTASection() {
  return (
    <section className="cta-band" aria-labelledby="cta-title">
      <div className="cta-band__inner shell">
        <Reveal>
          <p className="tag">Signal</p>
          <h2 id="cta-title">Something interesting is being built.</h2>
          <p>The lab is always open. Bring a question, or bring a broken thing.</p>
          <div className="cta-row">
            <Link className="btn btn--primary" to="/contact">
              Enter Thridha Labs
            </Link>
            <Link className="btn btn--ghost" to="/projects?type=experiment">
              View experiments
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function HomePage() {
  const { data: settings } = useSiteSettings()
  const siteName = settings?.general.site_name || 'Thridha Labs'
  const tagline = settings?.general.tagline || 'We experiment with intelligence.'
  const description =
    settings?.general.description || 'AI, software and ideas turned into things people can actually use.'

  const projects = usePublicProjects({ sort: 'display_order', order: 'asc' })
  const clients = usePublicClients({ sort: 'display_order', order: 'asc' })
  const testimonials = usePublicTestimonials({ sort: 'display_order', order: 'asc' })
  const brandingOgImage = useBrandingOgImage()

  usePageMeta({
    title: `${siteName} — ${tagline}`,
    description,
    canonical: absolutePageUrl('/'),
    ogTitle: settings?.seo?.seo_title || `${siteName} — ${tagline}`,
    ogDescription: settings?.seo?.seo_description || description,
    ogImage: brandingOgImage,
  })
  useJsonLd([
    {
      '@context': 'https://schema.org',
      '@type': 'WebSite',
      name: siteName,
      url: absolutePageUrl('/') ?? undefined,
      description,
    },
    settings?.contact?.contact_email
      ? {
          '@context': 'https://schema.org',
          '@type': 'Organization',
          name: siteName,
          url: absolutePageUrl('/') ?? undefined,
          description,
          email: settings.contact.contact_email,
          ...(settings?.contact?.address ? { address: settings.contact.address } : {}),
        }
      : {
          '@context': 'https://schema.org',
          '@type': 'Organization',
          name: siteName,
          url: absolutePageUrl('/') ?? undefined,
          description,
        },
  ])

  const sortedProjects = [...(projects.data?.items ?? [])].sort(
    (a, b) => Number(b.featured) - Number(a.featured) || a.display_order - b.display_order,
  )
  const selected = sortedProjects.slice(0, 5)
  const excluded = new Set(selected.map((project) => project.slug))

  return (
    <>
      <HeroSection siteName={siteName} tagline={tagline} description={description} />
      <IntroSection siteName={siteName} description={description} />
      <SelectedWorkSection
        projects={selected}
        error={projects.error}
        reload={projects.reload}
      />
      <ClientsSection
        clients={clients.data?.items ?? []}
        error={clients.error}
        reload={clients.reload}
      />
      <ExperimentsSection projects={sortedProjects} excluded={excluded} />
      <ActivityCarousel />
      <TestimonialsSection
        items={testimonials.data?.items ?? []}
        error={testimonials.error}
        reload={testimonials.reload}
      />
      <PhilosophySection siteName={siteName} />
      <CTASection />
    </>
  )
}