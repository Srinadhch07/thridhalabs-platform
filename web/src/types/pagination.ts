/** Pagination envelope used by every list endpoint. */

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}