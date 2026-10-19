/**
 * Public site footer — brand/tagline column, site links and contact details
 * pulled from site settings. Renders only the channels that are configured.
 */

import { Link } from 'react-router-dom'
import { useCareers } from '../../app/providers/CareersProvider'
import { useSiteSettings } from '../../app/providers/SiteSettingsProvider'

const BASE_SITE_LINKS = [
  { to: '/projects', label: 'Projects' },
  { to: '/activities', label: 'Activities' },
  { to: '/clients', label: 'Clients' },
  { to: '/testimonials', label: 'Testimonials' },
  { to: '/about', label: 'About' },
  { to: '/contact', label: 'Contact' },
] as const

export function Footer() {
  const { data: settings } = useSiteSettings()
  const { enabled: careersEnabled } = useCareers()
  const tagline = settings?.general.tagline || 'We experiment with intelligence.'
  const copyright = settings?.footer.copyright_text || `© ${new Date().getFullYear()} Thridha Labs`
  const contact = settings?.contact
  const socials = settings?.social?.urls ?? {}

  const siteLinks = careersEnabled
    ? [...BASE_SITE_LINKS, { to: '/careers', label: 'Careers' }]
    : BASE_SITE_LINKS

  const hasContact = Boolean(
    contact?.contact_email || contact?.contact_phone || contact?.whatsapp || contact?.address,
  )
  const hasSocials = Object.keys(socials).length > 0

  return (
    <footer className="site-footer public-footer">
      <div className="shell public-footer__grid">
        <div className="public-footer__brand">
          <Link to="/" className="public-brand" aria-label="Thridha Labs">
            <span className="public-brand__dot" aria-hidden="true" />
            Thridha&nbsp;<span className="public-brand__ghost">Labs</span>
          </Link>
          <p className="public-footer__tagline">{tagline}</p>
        </div>

        <div>
          <h2 className="public-footer__title">Explore</h2>
          <ul className="public-footer__links">
            {siteLinks.map((link) => (
              <li key={link.to}>
                <Link to={link.to}>{link.label}</Link>
              </li>
            ))}
          </ul>
        </div>

        {(hasContact || hasSocials) && (
          <div>
            <h2 className="public-footer__title">Contact</h2>
            <ul className="public-footer__contact">
              {contact?.contact_email && (
                <li>
                  <a href={`mailto:${contact.contact_email}`}>{contact.contact_email}</a>
                </li>
              )}
              {contact?.whatsapp && <li>{contact.whatsapp}</li>}
              {contact?.contact_phone && <li>{contact.contact_phone}</li>}
              {contact?.address && <li>{contact.address}</li>}
              {Object.entries(socials).map(([name, url]) => (
                <li key={name}>
                  <a href={url} target="_blank" rel="noreferrer">
                    {name}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="shell public-footer__bar">
        <span>{copyright}</span>
        <span>Built in-house — HTML, CSS &amp; React</span>
        <span>Websites · Applications · Experiments</span>
      </div>
    </footer>
  )
}