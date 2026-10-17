/** Admin pagination controls. */

export interface PaginationProps {
  page: number
  pages: number
  total: number
  onChange: (page: number) => void
}

export function Pagination({ page, pages, total, onChange }: PaginationProps) {
  if (pages <= 1) return null
  return (
    <nav className="pagination" aria-label="Pagination">
      <button
        type="button"
        className="btn btn--ghost btn--sm"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
      >
        Prev
      </button>
      <span className="pagination__info">
        Page {page} of {pages} · {total} item{total === 1 ? '' : 's'}
      </span>
      <button
        type="button"
        className="btn btn--ghost btn--sm"
        disabled={page >= pages}
        onClick={() => onChange(page + 1)}
      >
        Next
      </button>
    </nav>
  )
}