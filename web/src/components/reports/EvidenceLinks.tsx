/** External evidence links attached to a report. Renders nothing when empty. */

export function EvidenceLinks({ links, id }: { links: string[]; id?: string }) {
  if (links.length === 0) return null
  return (
    <div className="report-card__links" id={id}>
      <span className="report-card__links-label">Evidence</span>
      <ul className="member-tags">
        {links.map((link) => (
          <li key={link}>
            <a
              className="member-tag"
              href={link}
              target="_blank"
              rel="noopener noreferrer nofollow"
            >
              {link}
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
}
