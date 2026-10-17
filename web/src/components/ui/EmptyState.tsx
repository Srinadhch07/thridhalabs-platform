/** Empty-state placeholder for collections with no content yet. */

export interface EmptyStateProps {
  title?: string
  description?: string
}

export function EmptyState({ title = 'Nothing here yet', description }: EmptyStateProps) {
  return (
    <div className="state-card">
      <h2 className="state-card__title">{title}</h2>
      {description && <p className="state-card__body">{description}</p>}
    </div>
  )
}