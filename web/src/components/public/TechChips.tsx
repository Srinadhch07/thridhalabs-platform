/** TechChips — mono tag cloud for a project's technology list. */

export function TechChips({ items, limit }: { items: string[]; limit?: number }) {
  if (items.length === 0) return null
  const shown = typeof limit === 'number' ? items.slice(0, limit) : items
  return (
    <p className="tech-chips" aria-label="Technologies used">
      {shown.map((tech) => (
        <span className="chip" key={tech}>
          {tech}
        </span>
      ))}
    </p>
  )
}