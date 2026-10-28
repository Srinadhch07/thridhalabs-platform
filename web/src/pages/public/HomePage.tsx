/**
 * Home page — the public Thridha Labs landing.
 *
 * Rebuilt as a Swiss editorial composition: an oversized type-driven hero with
 * the restrained CosmicField backdrop, then a disciplined sequence of
 * numbered, asymmetrically aligned sections (selected work, capabilities,
 * programmes, collaborators, signal, closing invitation).
 *
 * Everything remains data-driven and theme-aware: every color is a branding
 * token (so the owner's palette — predefined or custom — drives the page),
 * and every section degrades gracefully. API errors render a section-level
 * retry; empty content hides the section entirely. No fabricated metrics.
 */

import { Link } from 'react-router-dom'
import { motion, useReducedMotion, type Variants } from 'framer-motion'
import { useSiteSettings } from '../../app/providers/SiteSettingsProvider'
import { CosmicField } from '../../components/ui/cosmic-field'
import { ClientTile } from '../../components/public/ClientTile'
import { ActivityCarousel } from '../../components/public/ActivityCarousel'
import { ProjectCard } from '../../components/public/ProjectCard'
import { Reveal } from '../../components/public/Reveal'
import { TechChips } from '../../components/public/TechChips'
import { TestimonialCard } from '../../components/public/TestimonialCard'
import { ErrorState } from '../../components/ui/ErrorState'
import { usePublicClients } from '../../features/clients/hooks'
import { usePublicProjects } from '../../features/projects/hooks'
import { usePublicTestimonials } from '../../features/testimonials/hooks'
import { usePageMeta, useBrandingOgImage, absolutePageUrl, siteShareImagePath } from '../../lib/utils/seo'
import { useJsonLd } from '../../lib/hooks/useJsonLd'
import type { PublicClient, PublicProject, PublicTestimonial } from '../../types/content'

/* ------------------------------------------------------------------ */
/* Hero                                                                */
/* ------------------------------------------------------------------ */

const HERO_STAGGER: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.09, delayChildren: 0.05 } },
}

const HERO_ITEM: Variants = {
  hidden: { opacity: 0, y: 22 },
  show: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}

function HeroSection() {
  const reduceMotion = useReducedMotion()
  const container: Variants = reduceMotion ? { hidden: {}, show: {} } : HERO_STAGGER
  const item: Variants = reduceMotion ? { hidden: { opacity: 1 }, show: { opacity: 1 } } : HERO_ITEM

  return (
    <section className="hero hero--editorial hero--refined-a" aria-labelledby="hero-title">
      <CosmicField />

      <motion.div className="shell hero-editorial hero-editorial--refined-a" variants={container} initial="hidden" animate="show">
        <motion.div variants={item}>
          <p className="hero-editorial__eyebrow hero-editorial__eyebrow--refined">
            AI-FIRST TECHNOLOGY &amp; EXPERIMENTATION LAB
          </p>
        </motion.div>

        <motion.h1 id="hero-title" className="hero-editorial__title hero-editorial__title--refined-a" variants={item}>
          AI systems that turn experiments into{' '}
          <span className="hero-editorial__title-emph">working products</span>
        </motion.h1>

        <motion.div className="hero-editorial__foot hero-editorial__foot--refined-a" variants={item}>
          <div className="hero-editorial__support-block">
            <p className="hero-editorial__support">
              Thridha Labs explores emerging AI, builds intelligent software, and solves real-world problems through applied research and product development.
            </p>
            <p className="hero-editorial__support hero-editorial__support--muted">
              From R&amp;D prototypes to client platforms and member-built tools.
            </p>
          </div>
          <div className="hero-editorial__actions">
            <div className="cta-row hero-editorial__cta">
              <Link className="btn btn--primary btn--refined" to="/projects">
                Explore our work &amp; experiments
              </Link>
              <Link className="btn btn--ghost btn--refined" to="/contact">
                Discuss a project
              </Link>
              <Link className="btn btn--ghost btn--refined" to="/careers">
                Lab Member opportunities
              </Link>
            </div>
            <p className="hero-editorial__microcopy">
              Applied AI • Intelligent Systems • Practical Delivery
            </p>
          </div>
        </motion.div>
      </motion.div>
    </section>
  )
}

export function HeroSectionA() {
  const reduceMotion = useReducedMotion()
  const container: Variants = reduceMotion ? { hidden: {}, show: {} } : HERO_STAGGER
  const item: Variants = reduceMotion ? { hidden: { opacity: 1 }, show: { opacity: 1 } } : HERO_ITEM

  return (
    <section className="hero hero--editorial hero--proto-a" aria-labelledby="hero-title-a">
      <CosmicField />

      <motion.div className="shell hero-editorial hero-editorial--proto-a" variants={container} initial="hidden" animate="show">
        <motion.div variants={item}>
          <p className="hero-editorial__eyebrow hero-editorial__eyebrow--mono">
            AI-FIRST EXPLORATION
          </p>
        </motion.div>

        <motion.h1 id="hero-title-a" className="hero-editorial__title hero-editorial__title--proto-a" variants={item}>
          INTELLIGENCE{' '}
          <span className="hero-editorial__title-glow">IN MOTION</span>
        </motion.h1>

        <motion.div className="hero-editorial__foot hero-editorial__foot--proto-a" variants={item}>
          <div className="hero-editorial__support-block">
            <p className="hero-editorial__support hero-editorial__support--mono">
              {reduceMotion ? '> ' : '> '}
              <span className="typing-cursor">Experimenting with agents, systems &amp; emergent behavior</span>
            </p>
            <p className="hero-editorial__support hero-editorial__support--mono">
              {'> '}Turning hypotheses into working intelligence
            </p>
          </div>
          <div className="cta-row hero-editorial__cta">
            <Link className="btn btn--primary btn--glow" to="/projects?type=experiment">
              &gt; Run experiments
            </Link>
            <Link className="btn btn--ghost btn--mono" to="/projects">
              &gt; View systems
            </Link>
            <Link className="btn btn--ghost btn--mono" to="/careers">
              &gt; Join the lab
            </Link>
          </div>
        </motion.div>
      </motion.div>
    </section>
  )
}

export function HeroSectionB() {
  const reduceMotion = useReducedMotion()
  const container: Variants = reduceMotion ? { hidden: {}, show: {} } : HERO_STAGGER
  const item: Variants = reduceMotion ? { hidden: { opacity: 1 }, show: { opacity: 1 } } : HERO_ITEM

  return (
    <section className="hero hero--editorial hero--proto-b" aria-labelledby="hero-title-b">
      <div className="hero-broadsheet__bg" aria-hidden="true" />
      <div className="hero-broadsheet__grid" aria-hidden="true" />

      <motion.div className="shell hero-editorial hero-editorial--proto-b" variants={container} initial="hidden" animate="show">
        <motion.div className="hero-broadsheet__kicker" variants={item}>
          <span className="hero-broadsheet__kicker-line">THRIDHA LABS / AI-FIRST TECHNOLOGY LAB</span>
          <span className="hero-broadsheet__kicker-line">EST. 2024 / EXPERIMENT → BUILD → SHIP</span>
        </motion.div>

        <motion.h1 id="hero-title-b" className="hero-editorial__title hero-editorial__title--proto-b" variants={item}>
          SYSTEMS{' '}
          <span className="hero-editorial__title-serif">OF INTELLIGENCE</span>
        </motion.h1>

        <motion.div className="hero-editorial__foot hero-editorial__foot--proto-b" variants={item}>
          <div className="hero-editorial__support-block">
            <p className="hero-editorial__support hero-editorial__support--broadsheet">
              A technology lab building intelligent products and platforms with rigor. We combine R&amp;D with real-world delivery for businesses and ambitious builders.
            </p>
            <div className="hero-broadsheet__meta">
              <span>Client Solutions</span>
              <span>•</span>
              <span>Lab Research</span>
              <span>•</span>
              <span>Member Projects</span>
            </div>
          </div>
          <div className="cta-row hero-editorial__cta hero-editorial__cta--broadsheet">
            <Link className="btn btn--primary btn--sharp" to="/contact">
              Start a project
            </Link>
            <Link className="btn btn--ghost btn--sharp" to="/careers">
              Lab Member Opportunities
            </Link>
            <Link className="btn btn--ghost btn--sharp" to="/projects">
              View portfolio
            </Link>
          </div>
        </motion.div>
      </motion.div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/* Section heading helper                                              */
/* ------------------------------------------------------------------ */

function EditorialHeader({
  index,
  label,
  title,
  action,
  id,
}: {
  index: string
  label: string
  title: string
  action?: { to: string; label: string }
  id?: string
}) {
  return (
    <Reveal className="ed-head">
      <p className="ed-head__index" aria-hidden="true">
        {index}
      </p>
      <div className="ed-head__main">
        <p className="ed-head__label">{label}</p>
        <h2 id={id} className="ed-head__title">
          {title}
        </h2>
      </div>
      {action && (
        <Link className="ed-head__action" to={action.to}>
          {action.label}
          <span className="arrow" aria-hidden="true">
            {' '}
            →
          </span>
        </Link>
      )}
    </Reveal>
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
          <EditorialHeader index="01" label="Selected work" title="Selected work." />
          <ErrorState title="Unable to load projects" error={error} onRetry={reload} />
        </div>
      </section>
    )
  }
  if (projects.length === 0) return null

  const [lead, ...rest] = projects
  return (
    <section className="section" aria-labelledby="selected-title">
      <div className="shell">
        <EditorialHeader
          id="selected-title"
          index="01"
          label="Selected work"
          title="Things we've built, running now."
          action={{ to: '/projects', label: 'All projects' }}
        />
        <div className="work-editorial">
          <Reveal className="work-editorial__lead">
            <ProjectCard featured project={lead} />
          </Reveal>
          {rest.length > 0 && (
            <div className="work-editorial__stack">
              {rest.map((project) => (
                <Reveal key={project.slug}>
                  <ProjectCard project={project} />
                </Reveal>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/* Practice — what the lab does (ecosystem framing)                    */
/* ------------------------------------------------------------------ */

const PRACTICE: Array<{ index: string; name: string; detail: string }> = [
  {
    index: '01',
    name: 'AI & intelligence',
    detail: 'Experiments with agents, language models and intelligent workflows.',
  },
  {
    index: '02',
    name: 'Products & systems',
    detail: 'Applications, tools and platforms built into working products.',
  },
  {
    index: '03',
    name: 'Client projects',
    detail: 'Websites and software delivered for real-world problems.',
  },
  {
    index: '04',
    name: 'Research & exploration',
    detail: 'Prototypes and emerging-technology investigations.',
  },
]

function PracticeSection() {
  return (
    <section className="section section--refined" aria-labelledby="practice-title">
      <div className="shell">
        <Reveal className="practice practice--refined">
          <div className="practice__intro">
            <p className="ed-head__label">
              CAPABILITIES
            </p>
            <h2 id="practice-title" className="ed-head__title ed-head__title--refined">
              Applied AI, built for real-world impact
            </h2>
            <p className="practice__lede">
              Thridha Labs bridges experimentation and delivery — combining research with practical engineering to ship intelligent systems that solve concrete problems.
            </p>
            <div className="practice-refined__highlights">
              <div className="practice-refined__highlight">
                <span className="practice-refined__dot" aria-hidden="true" />
                <span>For clients: AI-powered platforms &amp; custom solutions</span>
              </div>
              <div className="practice-refined__highlight">
                <span className="practice-refined__dot" aria-hidden="true" />
                <span>For members: build, showcase, and grow with the lab</span>
              </div>
            </div>
          </div>
          <ul className="practice__list practice__list--refined">
            {PRACTICE.map((item, index) => (
              <li key={item.name} className="practice-item practice-item--refined">
                <Reveal delay={index * 70}>
                  <span className="practice-item__index practice-item__index--refined" aria-hidden="true">
                    {item.index}
                  </span>
                  <div className="practice-item__body">
                    <span className="practice-item__name">{item.name}</span>
                    <span className="practice-item__detail">{item.detail}</span>
                  </div>
                </Reveal>
              </li>
            ))}
          </ul>
        </Reveal>
      </div>
    </section>
  )
}

export function PracticeSectionA() {
  return (
    <section className="section section--proto-a" aria-labelledby="practice-title-a">
      <div className="shell">
        <Reveal className="practice practice--proto-a">
          <div className="practice__intro">
            <p className="ed-head__label ed-head__label--mono">
              SYSTEM MAP
            </p>
            <h2 id="practice-title-a" className="ed-head__title ed-head__title--mono">
              R&amp;D → PROTOTYPE → DEPLOY
            </h2>
            <p className="practice__lede practice__lede--mono">
              Each experiment yields a module. Modules compose into systems. Systems ship as products.
            </p>
          </div>
          <ul className="practice__list practice__list--proto-a">
            {PRACTICE.map((item, index) => (
              <li key={item.name} className="practice-item practice-item--proto-a">
                <Reveal delay={index * 60}>
                  <span className="practice-item__index practice-item__index--mono" aria-hidden="true">
                    {item.index}
                  </span>
                  <div className="practice-item__body">
                    <span className="practice-item__name practice-item__name--mono">{item.name}</span>
                    <span className="practice-item__detail practice-item__detail--mono">{item.detail}</span>
                  </div>
                </Reveal>
              </li>
            ))}
          </ul>
        </Reveal>
      </div>
    </section>
  )
}

export function PracticeSectionB() {
  return (
    <section className="section section--proto-b" aria-labelledby="practice-title-b">
      <div className="shell">
        <Reveal className="practice practice--proto-b">
          <div className="practice__intro">
            <p className="ed-head__label">Practice</p>
            <h2 id="practice-title-b" className="ed-head__title ed-head__title--broadsheet">
              Disciplined experimentation for measurable outcomes.
            </h2>
            <p className="practice__lede">
              From strategic R&amp;D to client delivery, we maintain the same standards of clarity, rigor, and craft.
            </p>
            <div className="practice-broadsheet__callouts">
              <div className="practice-broadsheet__callout">
                <span className="practice-broadsheet__callout-num">01</span>
                <span>Clarity over complexity</span>
              </div>
              <div className="practice-broadsheet__callout">
                <span className="practice-broadsheet__callout-num">02</span>
                <span>Evidence over claims</span>
              </div>
              <div className="practice-broadsheet__callout">
                <span className="practice-broadsheet__callout-num">03</span>
                <span>Systems over one-offs</span>
              </div>
            </div>
          </div>
          <ul className="practice__list practice__list--proto-b">
            {PRACTICE.map((item, index) => (
              <li key={item.name} className="practice-item practice-item--proto-b">
                <Reveal delay={index * 80}>
                  <span className="practice-item__index" aria-hidden="true">
                    {item.index}
                  </span>
                  <div className="practice-item__body">
                    <span className="practice-item__name">{item.name}</span>
                    <span className="practice-item__detail">{item.detail}</span>
                  </div>
                </Reveal>
              </li>
            ))}
          </ul>
        </Reveal>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/* Process — QUESTION → EXPERIMENT → BUILD → LEARN                     */
/* ------------------------------------------------------------------ */

const PROCESS_STEPS = ['Question', 'Experiment', 'Build', 'Learn'] as const

function ProcessSection() {
  return (
    <section className="section section--compact" aria-labelledby="process-title">
      <div className="shell">
        <Reveal className="process">
          <p className="ed-head__label">How we work</p>
          <h2 id="process-title" className="visually-hidden">
            How we work
          </h2>
          <ol className="process__list">
            {PROCESS_STEPS.map((step, index) => (
              <li key={step} className="process__step">
                <span className="process__num" aria-hidden="true">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <span className="process__name">{step}</span>
                {index < PROCESS_STEPS.length - 1 && (
                  <span className="process__arrow" aria-hidden="true">
                    →
                  </span>
                )}
              </li>
            ))}
          </ol>
        </Reveal>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/* Collaborators                                                       */
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
          <EditorialHeader index="04" label="Collaborators" title="People we build with" />
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
        <EditorialHeader
          id="clients-title"
          index="04"
          label="Collaborators"
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
/* Technology                                                          */
/* ------------------------------------------------------------------ */

function TechnologySection({ projects }: { projects: PublicProject[] }) {
  const technologies = [...new Set(projects.flatMap((project) => project.technologies))].slice(0, 18)
  if (technologies.length === 0) return null

  return (
    <section className="section section--compact" aria-labelledby="tech-title">
      <div className="shell">
        <Reveal>
          <h2 id="tech-title" className="ed-head__label">
            Technology in use
          </h2>
          <TechChips items={technologies} />
        </Reveal>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/* Signal (testimonials)                                               */
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
          <EditorialHeader index="05" label="Signal" title="What people say." />
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
        <EditorialHeader
          id="testimonials-title"
          index="05"
          label="Signal"
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
/* Closing CTA                                                         */
/* ------------------------------------------------------------------ */

function ClosingSection() {
  return (
    <section className="closing" aria-labelledby="closing-title">
      <div className="shell closing__inner">
        <Reveal>
          <p className="ed-head__label">Work with the lab</p>
          <h2 id="closing-title" className="closing__title">
            Have an idea worth experimenting on?
          </h2>
          <p className="closing__lede">
            Bring a question, a rough concept or a real problem. We'll explore it and build
            what works.
          </p>
          <div className="cta-row closing__cta">
            <Link className="btn btn--primary" to="/contact">
              Start a project
            </Link>
            <Link className="btn btn--ghost" to="/projects?type=experiment">
              Explore our experiments
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
  const description = settings?.general.description || 'Thridha Labs is an AI-first experimental technology lab offering web development services, AI application development, agentic AI systems, and custom software development.'
    settings?.general.description || 'Thridha Labs is an AI-first experimental technology lab offering web development services, AI application development, agentic AI systems, and custom software development.'

  const projects = usePublicProjects({ sort: 'display_order', order: 'asc' })
  const clients = usePublicClients({ sort: 'display_order', order: 'asc' })
  const testimonials = usePublicTestimonials({ sort: 'display_order', order: 'asc' })
  const brandingOgImage = useBrandingOgImage()
  const siteOgImage = absolutePageUrl(siteShareImagePath())

  usePageMeta({
    title: siteName + ' - AI-first Technology Lab | Custom AI, Web Development & Agentic Systems',
    description,
    canonical: absolutePageUrl('/'),
    ogTitle: settings?.seo?.seo_title || (siteName + ' - AI-first Technology Lab | Custom AI, Web Development & Agentic Systems'),
    ogDescription: settings?.seo?.seo_description || description,
    ogImage: siteOgImage ?? brandingOgImage,
    ogImageAlt: siteName + ' - AI-first Technology Lab',
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

  return (
    <>
      <HeroSection />
      <PracticeSection />
      <SelectedWorkSection projects={selected} error={projects.error} reload={projects.reload} />
      <ProcessSection />
      <TechnologySection projects={sortedProjects} />
      <ActivityCarousel />
      <ClientsSection
        clients={clients.data?.items ?? []}
        error={clients.error}
        reload={clients.reload}
      />
      <TestimonialsSection
        items={testimonials.data?.items ?? []}
        error={testimonials.error}
        reload={testimonials.reload}
      />
      <ClosingSection />
    </>
  )
}
