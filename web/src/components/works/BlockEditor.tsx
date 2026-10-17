/**
 * BlockEditor — custom editor for a work's structured content document.
 *
 * Edits the validated block schema only (never HTML). Each block type gets a
 * focused sub-editor; blocks can be reordered, removed and added. Images are
 * uploaded in place through the shared contextual image fields.
 */

import { FormField } from '../form/FormField'
import { Select } from '../form/Select'
import { TextInput } from '../form/TextInput'
import { Textarea } from '../form/Textarea'
import { ImageGalleryField, ImageUploadField } from '../form/ImageUploadField'
import { uploadMemberMedia } from '../../features/media/api'
import type { ContentBlock, ContentBlockType, ContentDocument } from '../../types/work'

const MAX_BLOCKS = 100

const BLOCK_TYPE_LABELS: Record<ContentBlockType, string> = {
  paragraph: 'Paragraph',
  heading: 'Heading',
  image: 'Image',
  image_gallery: 'Image gallery',
  bulleted_list: 'Bulleted list',
  numbered_list: 'Numbered list',
  quote: 'Quote',
  code: 'Code',
  external_link: 'External link',
  divider: 'Divider',
}

const BLOCK_TYPE_ORDER: ContentBlockType[] = [
  'paragraph',
  'heading',
  'image',
  'image_gallery',
  'bulleted_list',
  'numbered_list',
  'quote',
  'code',
  'external_link',
  'divider',
]

export function createBlock(type: ContentBlockType): ContentBlock {
  switch (type) {
    case 'paragraph':
      return { type: 'paragraph', spans: [{ text: '' }] }
    case 'heading':
      return { type: 'heading', level: 2, text: '' }
    case 'image':
      return { type: 'image', media_id: '', caption: '', alt: '' }
    case 'image_gallery':
      return { type: 'image_gallery', media_ids: [] }
    case 'bulleted_list':
      return { type: 'bulleted_list', items: [''] }
    case 'numbered_list':
      return { type: 'numbered_list', items: [''] }
    case 'quote':
      return { type: 'quote', text: '', attribution: '' }
    case 'code':
      return { type: 'code', code: '', language: 'text' }
    case 'external_link':
      return { type: 'external_link', label: '', url: '' }
    case 'divider':
      return { type: 'divider' }
  }
}

function ListItemsEditor({
  id,
  items,
  onChange,
  itemLabel,
  disabled,
}: {
  id: string
  items: string[]
  onChange: (items: string[]) => void
  itemLabel: string
  disabled?: boolean
}) {
  return (
    <div className="block-list">
      {items.map((item, index) => (
        <div className="block-list__row" key={index}>
          <TextInput
            id={`${id}-item-${index}`}
            aria-label={`${itemLabel} ${index + 1}`}
            value={item}
            disabled={disabled}
            onChange={(value) => onChange(items.map((existing, i) => (i === index ? value : existing)))}
          />
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            disabled={disabled || items.length <= 1}
            onClick={() => onChange(items.filter((_, i) => i !== index))}
          >
            Remove
          </button>
        </div>
      ))}
      <button
        type="button"
        className="btn btn--ghost btn--sm"
        disabled={disabled}
        onClick={() => onChange([...items, ''])}
      >
        Add item
      </button>
    </div>
  )
}

function BlockBody({
  block,
  index,
  onChange,
  disabled,
}: {
  block: ContentBlock
  index: number
  onChange: (block: ContentBlock) => void
  disabled?: boolean
}) {
  switch (block.type) {
    case 'paragraph':
      return (
        <FormField id={`block-${index}-text`} label="Text">
          <Textarea
            id={`block-${index}-text`}
            rows={3}
            value={block.spans.map((span) => span.text).join('')}
            disabled={disabled}
            onChange={(value) => onChange({ type: 'paragraph', spans: [{ text: value }] })}
          />
        </FormField>
      )
    case 'heading':
      return (
        <div className="block-heading">
          <FormField id={`block-${index}-level`} label="Level">
            <Select
              id={`block-${index}-level`}
              value={String(block.level)}
              disabled={disabled}
              options={[
                { value: '2', label: 'Heading 2' },
                { value: '3', label: 'Heading 3' },
                { value: '4', label: 'Heading 4' },
              ]}
              onChange={(value) => onChange({ ...block, level: Number(value) as 2 | 3 | 4 })}
            />
          </FormField>
          <FormField id={`block-${index}-heading-text`} label="Heading text">
            <TextInput
              id={`block-${index}-heading-text`}
              value={block.text}
              disabled={disabled}
              onChange={(value) => onChange({ ...block, text: value })}
            />
          </FormField>
        </div>
      )
    case 'image':
      return (
        <div className="block-media">
          <ImageUploadField
            id={`block-${index}-media`}
            label="Image"
            value={block.media_id || null}
            onChange={(mediaId) => onChange({ ...block, media_id: mediaId ?? '' })}
            upload={uploadMemberMedia}
            disabled={disabled}
          />
          <div className="block-media__meta">
            <FormField id={`block-${index}-caption`} label="Caption">
              <TextInput
                id={`block-${index}-caption`}
                value={block.caption ?? ''}
                disabled={disabled}
                onChange={(value) => onChange({ ...block, caption: value })}
              />
            </FormField>
            <FormField id={`block-${index}-alt`} label="Alt text" hint="Describe the image">
              <TextInput
                id={`block-${index}-alt`}
                value={block.alt ?? ''}
                disabled={disabled}
                onChange={(value) => onChange({ ...block, alt: value })}
              />
            </FormField>
          </div>
        </div>
      )
    case 'image_gallery':
      return (
        <ImageGalleryField
          id={`block-${index}-gallery`}
          label="Gallery images"
          value={block.media_ids}
          onChange={(mediaIds) => onChange({ ...block, media_ids: mediaIds })}
          upload={uploadMemberMedia}
          disabled={disabled}
        />
      )
    case 'bulleted_list':
      return (
        <ListItemsEditor
          id={`block-${index}-bulleted`}
          items={block.items}
          itemLabel="Bullet"
          disabled={disabled}
          onChange={(items) => onChange({ ...block, items })}
        />
      )
    case 'numbered_list':
      return (
        <ListItemsEditor
          id={`block-${index}-numbered`}
          items={block.items}
          itemLabel="Item"
          disabled={disabled}
          onChange={(items) => onChange({ ...block, items })}
        />
      )
    case 'quote':
      return (
        <>
          <FormField id={`block-${index}-quote`} label="Quote">
            <Textarea
              id={`block-${index}-quote`}
              rows={3}
              value={block.text}
              disabled={disabled}
              onChange={(value) => onChange({ ...block, text: value })}
            />
          </FormField>
          <FormField id={`block-${index}-attribution`} label="Attribution">
            <TextInput
              id={`block-${index}-attribution`}
              value={block.attribution ?? ''}
              disabled={disabled}
              onChange={(value) => onChange({ ...block, attribution: value })}
            />
          </FormField>
        </>
      )
    case 'code':
      return (
        <>
          <FormField id={`block-${index}-code`} label="Code">
            <Textarea
              id={`block-${index}-code`}
              rows={5}
              value={block.code}
              disabled={disabled}
              onChange={(value) => onChange({ ...block, code: value })}
            />
          </FormField>
          <FormField id={`block-${index}-language`} label="Language">
            <TextInput
              id={`block-${index}-language`}
              value={block.language}
              disabled={disabled}
              onChange={(value) => onChange({ ...block, language: value })}
            />
          </FormField>
        </>
      )
    case 'external_link':
      return (
        <>
          <FormField id={`block-${index}-link-label`} label="Label" required>
            <TextInput
              id={`block-${index}-link-label`}
              value={block.label}
              disabled={disabled}
              onChange={(value) => onChange({ ...block, label: value })}
            />
          </FormField>
          <FormField id={`block-${index}-link-url`} label="URL" hint="https://…" required>
            <TextInput
              id={`block-${index}-link-url`}
              type="url"
              value={block.url}
              disabled={disabled}
              onChange={(value) => onChange({ ...block, url: value })}
            />
          </FormField>
        </>
      )
    case 'divider':
      return <p className="block-divider-note">A horizontal divider.</p>
  }
}

export interface BlockEditorProps {
  id?: string
  document: ContentDocument
  onChange: (document: ContentDocument) => void
  disabled?: boolean
}

export function BlockEditor({ id, document, onChange, disabled }: BlockEditorProps) {
  function replaceBlock(index: number, block: ContentBlock): void {
    onChange({ ...document, blocks: document.blocks.map((b, i) => (i === index ? block : b)) })
  }

  function removeBlock(index: number): void {
    onChange({ ...document, blocks: document.blocks.filter((_, i) => i !== index) })
  }

  function moveBlock(index: number, direction: -1 | 1): void {
    const target = index + direction
    if (target < 0 || target >= document.blocks.length) return
    const blocks = [...document.blocks]
    const [moved] = blocks.splice(index, 1)
    blocks.splice(target, 0, moved)
    onChange({ ...document, blocks })
  }

  function addBlock(type: ContentBlockType): void {
    if (document.blocks.length >= MAX_BLOCKS) return
    onChange({ ...document, blocks: [...document.blocks, createBlock(type)] })
  }

  return (
    <div className="block-editor" id={id}>
      {document.blocks.length === 0 ? (
        <p className="block-editor__empty">No blocks yet. Add one below to start building.</p>
      ) : null}

      <ol className="block-editor__list">
        {document.blocks.map((block, index) => (
          <li className="block-card" key={index}>
            <div className="block-card__bar">
              <span className="block-card__type">{BLOCK_TYPE_LABELS[block.type]}</span>
              <div className="block-card__actions">
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  disabled={disabled || index === 0}
                  aria-label={`Move ${BLOCK_TYPE_LABELS[block.type]} up`}
                  onClick={() => moveBlock(index, -1)}
                >
                  ↑
                </button>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  disabled={disabled || index === document.blocks.length - 1}
                  aria-label={`Move ${BLOCK_TYPE_LABELS[block.type]} down`}
                  onClick={() => moveBlock(index, 1)}
                >
                  ↓
                </button>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  disabled={disabled}
                  aria-label={`Remove ${BLOCK_TYPE_LABELS[block.type]}`}
                  onClick={() => removeBlock(index)}
                >
                  Remove
                </button>
              </div>
            </div>
            <div className="block-card__body">
              <BlockBody
                block={block}
                index={index}
                disabled={disabled}
                onChange={(next) => replaceBlock(index, next)}
              />
            </div>
          </li>
        ))}
      </ol>

      <div className="block-editor__add" role="group" aria-label="Add a block">
        <span className="block-editor__add-label">Add block</span>
        {BLOCK_TYPE_ORDER.map((type) => (
          <button
            key={type}
            type="button"
            className="btn btn--ghost btn--sm"
            disabled={disabled || document.blocks.length >= MAX_BLOCKS}
            onClick={() => addBlock(type)}
          >
            {BLOCK_TYPE_LABELS[type]}
          </button>
        ))}
      </div>
    </div>
  )
}
