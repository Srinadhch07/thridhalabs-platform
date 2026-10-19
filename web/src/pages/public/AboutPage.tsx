/**
 * About page — identity, the operating loop and how the lab works.
 * Narrative copy is settings-driven with brand fallbacks; no fabricated
 * history, awards or team claims.
 */

import { Link } from 'react-router-dom'
import { useSiteSettings } from '../../app/providers/SiteSettingsProvider'
import { PageHeader } from '../../components/public/PageHeader'
import { Reveal } from '../../components/public/Reveal'
import { absolutePageUrl, useDefaultOgImage, usePageMeta } from '../../lib/utils/seo'

function principle(step: string, title: string, body: string) {
  return (
    <li className="mode-item">
      <span className="mode-item__index">{step}</span>
      <span className="mode-item__name">{title}</span>
      <span className="mode-item__desc">{body}</span>
    </li>
  )
}

export default function AboutPage() {
  const { data: settings } = useSiteSettings()
  const siteName = settings?.general.site_name || 'Thridha Labs'
  const tagline = settings?.general.tagline || 'We experiment with intelligence.'
  const description =
    settings?.general.description || 'AI, software and ideas turned into things people can actually use.'

  const brandingOgImage = useDefaultOgImage()
  usePageMeta({
    title: 'About — Thridha Labs',
    description,
    canonical: absolutePageUrl('/about'),
    ogImage: brandingOgImage,
  })

  return (
    <>
      <PageHeader
        eyebrow="About / the unit"
        title={`About ${siteName}`}
        lede={`${tagline} ${description}`}
      />

      <section className="section" aria-labelledby="about-loop-title">
        <div className="shell about-columns">
          <Reveal>
            <p className="tag section-head__tag">
              <span className="hud-dot" aria-hidden="true" /> The loop
            </p>
            <h2 id="about-loop-title" className="about-loop-title">
              Build. Break. Learn. Repeat.
            </h2>
          </Reveal>
          <Reveal delay={120} className="intro-copy">
            <p>
              <strong>{siteName}</strong> is an experimental technology unit. {description}
            </p>
            <p>
              No ceremony, no roadmap theatre — the loop is run honestly and the results are
              published as they land.
            </p>
            <ul className="mode-list">
              {principle('01', 'Research', "What's next")}
              {principle('02', 'Build', 'How it works')}
              {principle('03', 'Test', 'What breaks')}
              {principle('04', 'Ship', 'What you get')}
            </ul>
          </Reveal>
        </div>
      </section>

      <section className="section" aria-labelledby="about-method-title">
        <div className="shell about-columns">
          <Reveal>
            <p className="tag section-head__tag">
              <span className="hud-dot" aria-hidden="true" /> Method
            </p>
            <h2 id="about-method-title" className="about-loop-title">
              Function before gloss.
            </h2>
          </Reveal>
          <Reveal delay={120} className="intro-copy">
            <p>
              Every project starts as a node in the lab — an idea, a broken thing, a question. The
              loop runs it into something usable, then ships it.
            </p>
            <p>
              We ship selected client work, our own products and open experiments. Everything on
              this site reads from the live archive: real projects, real clients, real signal.
            </p>
            <div className="cta-row">
              <Link className="btn btn--primary" to="/projects">
                See the work
              </Link>
              <Link className="btn btn--ghost" to="/contact">
                Bring a question
              </Link>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  )
}