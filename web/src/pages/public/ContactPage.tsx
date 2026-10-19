/**
 * Contact page — an art-directed "start a conversation" experience.
 *
 * Channels come from site settings (email, WhatsApp, phone, address); there is
 * still no public message endpoint, so the page leads with the fastest routes
 * and lists social links when configured. Visual language: editorial technology
 * lab — expressive type, a connected-systems motif and the shared cosmic
 * backdrop, all driven by the runtime branding theme.
 */

import { useSiteSettings } from '../../app/providers/SiteSettingsProvider'
import { CosmicField } from '../../components/ui/cosmic-field'
import { Reveal } from '../../components/public/Reveal'
import { absolutePageUrl, useBrandingOgImage, usePageMeta } from '../../lib/utils/seo'

/** Rebuild a WhatsApp conversation link from a configured value when possible. */
function whatsappHref(value: string): string | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  if (/^https?:\/\//i.test(trimmed)) return trimmed
  const digits = trimmed.replace(/[^\d+]/g, '')
  if (digits.replace(/\+/g, '').length < 6) return null
  return `https://wa.me/${digits.replace(/^\+/, '')}`
}

/** A restrained connected-systems / technical diagram for the hero. */
function ContactDiagram() {
  return (
    <svg
      className="contact-hero__diagram"
      viewBox="0 0 340 340"
      role="img"
      aria-label="A composed orbital diagram: an intelligence core connected to nodes on concentric rings, suggesting interconnected systems and experimentation"
    >
      <defs>
        <radialGradient id="contact-core" cx="50%" cy="50%" r="50%">
          <stop offset="0%" className="contact-hero__grad-core-inner" />
          <stop offset="42%" className="contact-hero__grad-core-mid" />
          <stop offset="100%" className="contact-hero__grad-core-outer" />
        </radialGradient>
        <radialGradient id="contact-halo" cx="50%" cy="50%" r="50%">
          <stop offset="0%" className="contact-hero__grad-halo-inner" />
          <stop offset="100%" className="contact-hero__grad-halo-outer" />
        </radialGradient>
        <filter id="contact-node-shadow" x="-60%" y="-60%" width="220%" height="220%">
          <feDropShadow dx="0" dy="1.5" stdDeviation="2.5" floodOpacity="0.45" />
        </filter>
      </defs>

      {/* Restrained lighting behind the core. */}
      <circle className="contact-hero__halo" cx="170" cy="170" r="150" fill="url(#contact-halo)" />

      {/* Concentric orbital rings — the composition's structure. */}
      <g className="contact-hero__diagram-orbits" aria-hidden="true">
        <ellipse cx="170" cy="170" rx="118" ry="118" transform="rotate(-18 170 170)" />
        <ellipse cx="170" cy="170" rx="86" ry="86" transform="rotate(-18 170 170)" />
        <ellipse cx="170" cy="170" rx="54" ry="54" transform="rotate(-18 170 170)" />
      </g>

      {/* Deliberate radial connectors from the core to each node. */}
      <g className="contact-hero__diagram-links" aria-hidden="true">
        <path d="M170 170 L170 52" />
        <path d="M170 170 L281 238" />
        <path d="M170 170 L62 246" />
        <path d="M170 170 L272 116" />
        <path d="M170 170 L74 108" />
      </g>

      {/* Intelligence core. */}
      <circle
        className="contact-hero__diagram-core"
        cx="170"
        cy="170"
        r="40"
        fill="url(#contact-core)"
      />
      <circle className="contact-hero__diagram-core-ring" cx="170" cy="170" r="40" />
      <circle className="contact-hero__diagram-core-dot" cx="170" cy="170" r="6" />

      {/* Nodes sitting on the rings. */}
      <g filter="url(#contact-node-shadow)">
        <circle className="contact-hero__diagram-node contact-hero__diagram-node--hub" cx="170" cy="52" r="9" />
        <circle className="contact-hero__diagram-node" cx="281" cy="238" r="7" />
        <circle className="contact-hero__diagram-node" cx="62" cy="246" r="7" />
        <circle className="contact-hero__diagram-node" cx="272" cy="116" r="7" />
        <circle className="contact-hero__diagram-node" cx="74" cy="108" r="7" />
      </g>
    </svg>
  )
}

const COLLABORATION = [
  {
    index: '01',
    title: 'Websites & applications',
    detail: 'New builds, rebuilds and the systems behind them — designed to work, not just to look new.',
  },
  {
    index: '02',
    title: 'Business digital presence',
    detail: 'A clearer, more useful online face for a business that has outgrown what it has.',
  },
  {
    index: '03',
    title: 'Product ideas & experiments',
    detail: 'Early concepts, technical bets and prototypes worth taking from sketch to something real.',
  },
  {
    index: '04',
    title: 'Collaboration & enquiries',
    detail: 'Partnerships, questions and anything worth a conversation with the lab.',
  },
]

export default function ContactPage() {
  const { data: settings } = useSiteSettings()
  const contact = settings?.contact
  const socials = settings?.social?.urls ?? {}
  const brandingOgImage = useBrandingOgImage()

  usePageMeta({
    title: 'Contact — Thridha Labs',
    description:
      "From a new digital idea to a business that needs a better online presence, let's explore what we can create together.",
    canonical: absolutePageUrl('/contact'),
    ogImage: brandingOgImage,
  })

  const hasContact = Boolean(
    contact?.contact_email || contact?.contact_phone || contact?.whatsapp || contact?.address,
  )
  const hasSocials = Object.keys(socials).length > 0
  const whatsappUrl = contact?.whatsapp ? whatsappHref(contact.whatsapp) : null

  return (
    <>
      <section className="contact-hero" aria-labelledby="contact-title">
        <CosmicField />
        <div className="shell contact-hero__inner">
          <div className="contact-hero__copy">
            <Reveal>
              <p className="eyebrow contact-hero__eyebrow">
                <span className="hud-dot" aria-hidden="true" />
                Contact / Start a conversation
              </p>
            </Reveal>
            <Reveal delay={60}>
              <h1 id="contact-title" className="contact-hero__title">
                Have something{' '}
                <span className="contact-hero__title-ghost">worth building?</span>
              </h1>
            </Reveal>
            <Reveal delay={120}>
              <p className="contact-hero__support">
                From a new digital idea to a business that needs a better online presence, let&apos;s
                explore what we can create together.
              </p>
            </Reveal>
            <Reveal delay={180}>
              <div className="cta-row contact-hero__cta">
                <a className="btn btn--primary" href="#reach">
                  Start a Conversation
                </a>
              </div>
            </Reveal>
          </div>
          <Reveal className="contact-hero__figure" delay={120}>
            <ContactDiagram />
          </Reveal>
        </div>
      </section>

      <section className="section section--compact" id="reach" aria-labelledby="reach-title">
        <div className="shell">
          <div className="ed-head">
            <p className="ed-head__index" aria-hidden="true">
              01
            </p>
            <div className="ed-head__main">
              <p className="ed-head__label">Reach the lab</p>
              <h2 id="reach-title" className="ed-head__title">
                The fastest ways in.
              </h2>
            </div>
          </div>

          {!hasContact && !hasSocials ? (
            <Reveal>
              <p className="contact-empty" role="status">
                Contact channels are not configured yet. Check back shortly — the fastest way in is
                usually email.
              </p>
            </Reveal>
          ) : (
            <div className="contact-methods">
              {contact?.contact_email ? (
                <Reveal>
                  <article className="contact-method">
                    <span className="contact-method__icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <rect x="2.5" y="5" width="19" height="14" rx="2" />
                        <path d="M3 7l9 6 9-6" />
                      </svg>
                    </span>
                    <h3 className="contact-method__heading">Email</h3>
                    <p className="contact-method__detail">
                      The most direct route. Tell us what you have in mind.
                    </p>
                    <a className="contact-method__link" href={`mailto:${contact.contact_email}`}>
                      {contact.contact_email}
                      <span className="contact-method__arrow" aria-hidden="true">
                        →
                      </span>
                    </a>
                  </article>
                </Reveal>
              ) : null}

              {contact?.whatsapp ? (
                <Reveal delay={60}>
                  <article className="contact-method">
                    <span className="contact-method__icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M20 11.5a8 8 0 0 1-11.9 7L4 19.5l1.1-3.9A8 8 0 1 1 20 11.5Z" />
                        <path d="M9 9.2c.2-.5.4-.5.7-.5h.5c.2 0 .4 0 .5.4l.6 1.4c.1.2 0 .4-.1.5l-.4.5c-.1.1-.2.3-.1.5.3.6.9 1.2 1.5 1.5.2.1.4 0 .5-.1l.5-.4c.1-.1.3-.2.5-.1l1.4.6c.4.1.4.3.4.5v.5c0 .3 0 .5-.5.7-.4.2-.9.3-1.5.1-1-.3-2-1-2.8-1.8-.8-.8-1.5-1.8-1.8-2.8-.2-.6-.1-1.1.1-1.5Z" />
                      </svg>
                    </span>
                    <h3 className="contact-method__heading">WhatsApp</h3>
                    <p className="contact-method__detail">
                      Quick questions and shorter conversations — message us directly.
                    </p>
                    {whatsappUrl ? (
                      <a
                        className="contact-method__link"
                        href={whatsappUrl}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {contact.whatsapp}
                        <span className="contact-method__arrow" aria-hidden="true">
                          →
                        </span>
                      </a>
                    ) : (
                      <p className="contact-method__link contact-method__link--static">
                        {contact.whatsapp}
                      </p>
                    )}
                  </article>
                </Reveal>
              ) : null}

              {contact?.contact_phone ? (
                <Reveal delay={120}>
                  <article className="contact-method">
                    <span className="contact-method__icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M5 3.5h3l1.5 4-2 1.5a12 12 0 0 0 5.5 5.5l1.5-2 4 1.5v3c0 .8-.7 1.5-1.5 1.5A15.5 15.5 0 0 1 3.5 5c0-.8.7-1.5 1.5-1.5Z" />
                      </svg>
                    </span>
                    <h3 className="contact-method__heading">Phone</h3>
                    <p className="contact-method__detail">Prefer to talk it through? Give us a call.</p>
                    <a className="contact-method__link" href={`tel:${contact.contact_phone}`}>
                      {contact.contact_phone}
                      <span className="contact-method__arrow" aria-hidden="true">
                        →
                      </span>
                    </a>
                  </article>
                </Reveal>
              ) : null}

              {contact?.address ? (
                <Reveal delay={180}>
                  <article className="contact-method">
                    <span className="contact-method__icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11Z" />
                        <circle cx="12" cy="10" r="2.5" />
                      </svg>
                    </span>
                    <h3 className="contact-method__heading">Address</h3>
                    <p className="contact-method__detail">Where the lab works from.</p>
                    <p className="contact-method__link contact-method__link--static">{contact.address}</p>
                  </article>
                </Reveal>
              ) : null}
            </div>
          )}

          {hasSocials && (
            <Reveal className="contact-socials">
              <h3 className="contact-socials__title">Elsewhere</h3>
              <div className="social-row">
                {Object.entries(socials).map(([name, url]) => (
                  <a key={name} className="btn btn--ghost" href={url} target="_blank" rel="noreferrer">
                    {name} <span aria-hidden="true">↗</span>
                  </a>
                ))}
              </div>
            </Reveal>
          )}
        </div>
      </section>

      <section className="section" aria-labelledby="collaborate-title">
        <div className="shell">
          <div className="ed-head">
            <p className="ed-head__index" aria-hidden="true">
              02
            </p>
            <div className="ed-head__main">
              <p className="ed-head__label">What we can build together</p>
              <h2 id="collaborate-title" className="ed-head__title">
                Bring us something worth making.
              </h2>
            </div>
          </div>
          <ol className="collab-list">
            {COLLABORATION.map((item) => (
              <Reveal key={item.index} className="collab-item">
                <span className="collab-item__index" aria-hidden="true">
                  {item.index}
                </span>
                <div className="collab-item__body">
                  <h3 className="collab-item__title">{item.title}</h3>
                  <p className="collab-item__detail">{item.detail}</p>
                </div>
              </Reveal>
            ))}
          </ol>
        </div>
      </section>

      <section className="closing" aria-labelledby="contact-closing-title">
        <div className="shell closing__inner">
          <Reveal>
            <p className="ed-head__label">Work with the lab</p>
            <h2 id="contact-closing-title" className="closing__title">
              Every good build starts with a conversation.
            </h2>
            <p className="closing__lede">
              Tell us what you&apos;re thinking about. We&apos;ll take it from there.
            </p>
            <div className="cta-row closing__cta">
              {contact?.contact_email ? (
                <a className="btn btn--primary" href={`mailto:${contact.contact_email}`}>
                  Email the lab
                </a>
              ) : null}
              {whatsappUrl ? (
                <a className="btn btn--ghost" href={whatsappUrl} target="_blank" rel="noreferrer">
                  Message on WhatsApp
                </a>
              ) : null}
              {!contact?.contact_email && !whatsappUrl ? (
                <a className="btn btn--primary" href="#reach">
                  Start a Conversation
                </a>
              ) : null}
            </div>
          </Reveal>
        </div>
      </section>
    </>
  )
}
