/**
 * Contact page — channels from site settings (email, WhatsApp, phone,
 * address). There is no public message endpoint yet, so the page leads with
 * the fastest route and lists social links when configured.
 */

import { useSiteSettings } from '../../app/providers/SiteSettingsProvider'
import { PageHeader } from '../../components/public/PageHeader'
import { Reveal } from '../../components/public/Reveal'
import { absolutePageUrl, useBrandingOgImage, usePageMeta } from '../../lib/utils/seo'

export default function ContactPage() {
  const { data: settings } = useSiteSettings()
  const contact = settings?.contact
  const socials = settings?.social?.urls ?? {}
  const brandingOgImage = useBrandingOgImage()

  usePageMeta({
    title: 'Contact — Thridha Labs',
    description:
      'The lab is always open. Bring a question, or bring a broken thing — reach Thridha Labs here.',
    canonical: absolutePageUrl('/contact'),
    ogImage: brandingOgImage,
  })

  const hasContact = Boolean(
    contact?.contact_email || contact?.contact_phone || contact?.whatsapp || contact?.address,
  )
  const hasSocials = Object.keys(socials).length > 0

  return (
    <>
      <PageHeader
        eyebrow="Contact / signal"
        title="Get in touch"
        lede="The lab is always open. Bring a question, or bring a broken thing."
      />

      <div className="shell" style={{ paddingBlock: 'var(--space-7)' }}>
        {!hasContact && !hasSocials ? (
          <Reveal>
            <p className="state-card__body" style={{ maxWidth: '52ch' }}>
              Contact channels are not configured yet. Check back shortly — the fastest way in is
              usually email.
            </p>
          </Reveal>
        ) : (
          <div className="contact-grid">
            {contact?.contact_email && (
              <Reveal>
                <div className="contact-card">
                  <p className="contact-card__label">Email</p>
                  <p className="contact-card__value">
                    <a href={`mailto:${contact.contact_email}`}>{contact.contact_email}</a>
                  </p>
                </div>
              </Reveal>
            )}
            {contact?.whatsapp && (
              <Reveal delay={60}>
                <div className="contact-card">
                  <p className="contact-card__label">WhatsApp</p>
                  <p className="contact-card__value">{contact.whatsapp}</p>
                </div>
              </Reveal>
            )}
            {contact?.contact_phone && (
              <Reveal delay={120}>
                <div className="contact-card">
                  <p className="contact-card__label">Phone</p>
                  <p className="contact-card__value">{contact.contact_phone}</p>
                </div>
              </Reveal>
            )}
            {contact?.address && (
              <Reveal delay={180}>
                <div className="contact-card">
                  <p className="contact-card__label">Address</p>
                  <p className="contact-card__value">{contact.address}</p>
                </div>
              </Reveal>
            )}
          </div>
        )}

        {hasSocials && (
          <section style={{ marginTop: 'var(--space-8)' }} aria-label="Social channels">
            <h2 className="public-footer__title">Elsewhere</h2>
            <div className="social-row">
              {Object.entries(socials).map(([name, url]) => (
                <a key={name} className="btn btn--ghost" href={url} target="_blank" rel="noreferrer">
                  {name} <span aria-hidden="true">↗</span>
                </a>
              ))}
            </div>
          </section>
        )}
      </div>
    </>
  )
}