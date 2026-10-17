/**
 * ContentRenderer — read-only renderer for a structured work content document.
 *
 * Renders only the validated block schema (never HTML); media is resolved by id
 * through the public media delivery route. Used by the member preview and the
 * public work page so the two always agree.
 */

import { Fragment, useState } from 'react'
import { resolveMediaUrl } from '../../lib/utils/mediaUrl'
import type { ContentBlock, ContentDocument, InlineRun } from '../../types/work'

function InlineRuns({ spans }: { spans: InlineRun[] }) {
  return (
    <>
      {spans.map((span, index) => {
        let node: React.ReactNode = span.text
        if (span.code) node = <code className="work-inline-code">{node}</code>
        if (span.italic) node = <em>{node}</em>
        if (span.bold) node = <strong>{node}</strong>
        if (span.link) {
          node = (
            <a href={span.link} target="_blank" rel="noreferrer">
              {node}
            </a>
          )
        }
        return <Fragment key={index}>{node}</Fragment>
      })}
    </>
  )
}

function WorkImage({ mediaId, alt, caption }: { mediaId: string; alt?: string | null; caption?: string | null }) {
  const [failed, setFailed] = useState(false)
  const src = failed ? null : resolveMediaUrl(mediaId, 'md')
  return (
    <figure className="work-figure">
      {src ? (
        <img className="work-figure__img" src={src} alt={alt ?? ''} loading="lazy" onError={() => setFailed(true)} />
      ) : (
        <span className="work-figure__missing" aria-hidden="true" />
      )}
      {caption ? <figcaption className="work-figure__caption">{caption}</figcaption> : null}
    </figure>
  )
}

function Block({ block }: { block: ContentBlock }) {
  switch (block.type) {
    case 'paragraph':
      if (block.spans.every((span) => !span.text.trim())) return null
      return (
        <p className="work-para">
          <InlineRuns spans={block.spans} />
        </p>
      )
    case 'heading': {
      const Tag = (block.level === 2 ? 'h2' : block.level === 3 ? 'h3' : 'h4') as 'h2' | 'h3' | 'h4'
      return <Tag className="work-heading">{block.text}</Tag>
    }
    case 'image':
      return <WorkImage mediaId={block.media_id} alt={block.alt} caption={block.caption} />
    case 'image_gallery':
      return (
        <div className="work-gallery">
          {block.media_ids.map((id) => (
            <WorkImage key={id} mediaId={id} />
          ))}
        </div>
      )
    case 'bulleted_list':
      return (
        <ul className="work-list">
          {block.items.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      )
    case 'numbered_list':
      return (
        <ol className="work-list">
          {block.items.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ol>
      )
    case 'quote':
      return (
        <blockquote className="work-quote">
          <p>{block.text}</p>
          {block.attribution ? <cite>— {block.attribution}</cite> : null}
        </blockquote>
      )
    case 'code':
      return (
        <pre className="work-code">
          <code>{block.code}</code>
        </pre>
      )
    case 'external_link':
      return (
        <p className="work-link-block">
          <a href={block.url} target="_blank" rel="noreferrer">
            {block.label} <span aria-hidden="true">↗</span>
          </a>
        </p>
      )
    case 'divider':
      return <hr className="work-divider" />
    default:
      return null
  }
}

export function ContentRenderer({ document }: { document: ContentDocument }) {
  const blocks = document.blocks
  if (blocks.length === 0) {
    return <p className="work-content-empty">This work has no content yet.</p>
  }
  return (
    <div className="work-content">
      {blocks.map((block, index) => (
        <Block key={index} block={block} />
      ))}
    </div>
  )
}
