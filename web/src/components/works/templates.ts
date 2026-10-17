/**
 * Client-side mirror of the backend work templates.
 *
 * Templates are just starting points — seeding them here lets the editor show
 * blocks immediately instead of round-tripping through the API.
 */

import { createBlock } from './BlockEditor'
import type { ContentBlock, ContentDocument, WorkTemplate } from '../../types/work'

export function seedTemplate(template: WorkTemplate): ContentDocument {
  const paragraph = (): ContentBlock => createBlock('paragraph')
  let blocks: ContentBlock[]

  switch (template) {
    case 'project-showcase':
      blocks = [
        { type: 'heading', level: 2, text: 'Overview' },
        paragraph(),
        { type: 'heading', level: 2, text: 'Highlights' },
        { type: 'bulleted_list', items: [''] },
        { type: 'divider' },
        { type: 'heading', level: 2, text: 'Results' },
        paragraph(),
      ]
      break
    case 'research':
      blocks = [
        { type: 'heading', level: 2, text: 'Question' },
        paragraph(),
        { type: 'heading', level: 2, text: 'Approach' },
        paragraph(),
        { type: 'numbered_list', items: [''] },
        { type: 'heading', level: 2, text: 'Findings' },
        { type: 'quote', text: '', attribution: '' },
      ]
      break
    case 'creative-portfolio':
      blocks = [
        { type: 'heading', level: 2, text: 'Concept' },
        paragraph(),
        { type: 'divider' },
        { type: 'heading', level: 2, text: 'Gallery' },
        { type: 'image_gallery', media_ids: [] },
        { type: 'divider' },
        { type: 'heading', level: 2, text: 'Process' },
        paragraph(),
      ]
      break
    default:
      blocks = [paragraph()]
  }

  return { version: 1, blocks }
}
