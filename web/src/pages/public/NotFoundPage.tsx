/** Application-level 404 page. */

import { NotFoundState } from '../../components/ui/NotFoundState'
import { usePageMeta } from '../../lib/utils/seo'

export default function NotFoundPage() {
  usePageMeta({ title: 'Page not found — Thridha Labs', robots: 'noindex, nofollow' })

  return (
    <div>
      <NotFoundState />
    </div>
  )
}