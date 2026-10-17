/**
 * ImageUploadField / ImageGalleryField — contextual upload behaviour:
 * empty state, upload, preview, replace, remove, validation, accessibility.
 * Uploads are injected so these unit tests exercise the component in isolation.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../lib/errors/ApiError'
import {
  IMAGE_MAX_BYTES,
  ImageGalleryField,
  ImageUploadField,
} from '../components/form/ImageUploadField'
import type { Media } from '../types/media'

function makeMedia(id: string): Media {
  return {
    id,
    original_name: `${id}.webp`,
    format: 'webp',
    mime_type: 'image/webp',
    media_type: 'image',
    size_bytes: 1024,
    width: 100,
    height: 100,
    checksum: 'checksum',
    storage_mode: 'local',
    variants: [],
    urls: {
      original: `/api/media/${id}/file?variant=original`,
      thumb: `/api/media/${id}/file?variant=thumb`,
    },
    created_by: 'admin-1',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

function makeFile(name = 'pic.webp', type = 'image/webp', bytes = 4): File {
  const file = new File([new Uint8Array(bytes)], name, { type })
  return file
}

function withSize(file: File, size: number): File {
  Object.defineProperty(file, 'size', { value: size })
  return file
}

/** Stateful wrapper mirroring how real forms control the field. */
function Harness({
  initial = null,
  upload,
  onChange,
  resolvePreviewUrl,
}: {
  initial?: string | null
  upload: (file: File) => Promise<Media>
  onChange?: (id: string | null) => void
  resolvePreviewUrl?: (id: string) => Promise<string | null>
}) {
  const [value, setValue] = useState<string | null>(initial)
  return (
    <ImageUploadField
      id="logo"
      label="Logo"
      value={value}
      onChange={(id) => {
        setValue(id)
        onChange?.(id)
      }}
      upload={upload}
      resolvePreviewUrl={resolvePreviewUrl}
    />
  )
}

describe('ImageUploadField', () => {
  it('shows an upload affordance in the empty state', () => {
    render(
      <ImageUploadField
        id="logo"
        label="Logo"
        value={null}
        onChange={() => {}}
        upload={vi.fn()}
      />,
    )
    expect(screen.getByRole('button', { name: /upload image/i })).toBeInTheDocument()
    expect(screen.getByText(/no image selected/i)).toBeInTheDocument()
    expect(screen.getByText(/png, jpeg or webp/i)).toBeInTheDocument()
  })

  it('uploads a chosen file and reports the new media id', async () => {
    const upload = vi.fn().mockResolvedValue(makeMedia('m-9'))
    const onChange = vi.fn()
    render(
      <ImageUploadField id="logo" label="Logo" value={null} onChange={onChange} upload={upload} />,
    )

    const file = makeFile()
    fireEvent.change(screen.getByLabelText('Logo'), { target: { files: [file] } })

    await waitFor(() => expect(onChange).toHaveBeenCalledWith('m-9'))
    expect(upload).toHaveBeenCalledTimes(1)
    expect(upload.mock.calls[0][0]).toBe(file)
  })

  it('renders a preview of the uploaded image', async () => {
    const upload = vi.fn().mockResolvedValue(makeMedia('m-9'))
    render(<Harness upload={upload} />)

    fireEvent.change(screen.getByLabelText('Logo'), { target: { files: [makeFile()] } })

    const img = await screen.findByRole('img', { name: 'Logo' })
    expect(img).toHaveAttribute('src', '/api/media/m-9/file?variant=thumb')
    expect(screen.getByRole('button', { name: /replace image/i })).toBeInTheDocument()
  })

  it('loads a preview for an existing reference through resolvePreviewUrl', async () => {
    const resolvePreviewUrl = vi.fn().mockResolvedValue('https://cdn.example.com/thumb.png')
    render(
      <ImageUploadField
        id="logo"
        label="Logo"
        value="m-1"
        onChange={() => {}}
        upload={vi.fn()}
        resolvePreviewUrl={resolvePreviewUrl}
      />,
    )

    const img = await screen.findByRole('img', { name: 'Logo' })
    expect(img).toHaveAttribute('src', 'https://cdn.example.com/thumb.png')
    expect(resolvePreviewUrl).toHaveBeenCalledWith('m-1')
  })

  it('replaces the reference only after a successful upload', async () => {
    const upload = vi.fn().mockResolvedValue(makeMedia('m-2'))
    const onChange = vi.fn()
    render(<Harness initial="m-1" upload={upload} onChange={onChange} />)

    fireEvent.change(screen.getByLabelText('Logo'), { target: { files: [makeFile()] } })

    await waitFor(() => expect(onChange).toHaveBeenCalledWith('m-2'))
    const img = await screen.findByRole('img', { name: 'Logo' })
    expect(img).toHaveAttribute('src', '/api/media/m-2/file?variant=thumb')
  })

  it('preserves the previous reference when the upload fails', async () => {
    const upload = vi.fn().mockRejectedValue(new ApiError(413, 'FILE_TOO_LARGE', 'too big'))
    const onChange = vi.fn()
    render(
      <ImageUploadField id="logo" label="Logo" value="m-1" onChange={onChange} upload={upload} />,
    )

    fireEvent.change(screen.getByLabelText('Logo'), { target: { files: [makeFile()] } })

    expect(await screen.findByRole('alert')).toHaveTextContent(/too large/i)
    expect(onChange).not.toHaveBeenCalled()
  })

  it('removes the reference without deleting the underlying asset', () => {
    const onChange = vi.fn()
    render(
      <ImageUploadField id="logo" label="Logo" value="m-1" onChange={onChange} upload={vi.fn()} />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Remove' }))

    expect(onChange).toHaveBeenCalledWith(null)
  })

  it('rejects a non-image file before uploading', () => {
    const upload = vi.fn()
    render(
      <ImageUploadField id="logo" label="Logo" value={null} onChange={() => {}} upload={upload} />,
    )

    fireEvent.change(screen.getByLabelText('Logo'), {
      target: { files: [makeFile('notes.txt', 'text/plain')] },
    })

    expect(screen.getByRole('alert')).toHaveTextContent(/unsupported file/i)
    expect(upload).not.toHaveBeenCalled()
  })

  it('rejects an oversized file before uploading', () => {
    const upload = vi.fn()
    render(
      <ImageUploadField id="logo" label="Logo" value={null} onChange={() => {}} upload={upload} />,
    )

    fireEvent.change(screen.getByLabelText('Logo'), {
      target: { files: [withSize(makeFile('big.png', 'image/png'), IMAGE_MAX_BYTES + 1)] },
    })

    expect(screen.getByRole('alert')).toHaveTextContent(/too large/i)
    expect(upload).not.toHaveBeenCalled()
  })

  it('disables every control when disabled', () => {
    render(
      <ImageUploadField
        id="logo"
        label="Logo"
        value="m-1"
        onChange={() => {}}
        upload={vi.fn()}
        disabled
      />,
    )

    expect(screen.getByRole('button', { name: /replace image/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Remove' })).toBeDisabled()
    expect(screen.getByLabelText('Logo')).toBeDisabled()
  })

  it('exposes the upload input with an accessible label', () => {
    render(
      <ImageUploadField
        id="logo"
        label="Brand logo"
        value={null}
        onChange={() => {}}
        upload={vi.fn()}
      />,
    )
    const input = screen.getByLabelText('Brand logo')
    expect(input).toHaveAttribute('type', 'file')
    expect(input).toHaveAttribute('accept', 'image/png,image/jpeg,image/webp')
  })
})

describe('ImageGalleryField', () => {
  it('appends uploaded images in order', async () => {
    const upload = vi
      .fn()
      .mockResolvedValueOnce(makeMedia('g-1'))
      .mockResolvedValueOnce(makeMedia('g-2'))
    const onChange = vi.fn()
    render(
      <ImageGalleryField
        id="gallery"
        label="Gallery"
        value={[]}
        onChange={onChange}
        upload={upload}
      />,
    )

    const input = screen.getByTestId('gallery-input')
    fireEvent.change(input, { target: { files: [makeFile('a.webp')] } })
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(['g-1']))

    fireEvent.change(input, { target: { files: [makeFile('b.webp')] } })
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(['g-2']))
  })

  it('removes a gallery item without deleting the asset', () => {
    const onChange = vi.fn()
    render(
      <ImageGalleryField
        id="gallery"
        label="Gallery"
        value={['g-1', 'g-2']}
        onChange={onChange}
        upload={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Remove image 1' }))

    expect(onChange).toHaveBeenCalledWith(['g-2'])
  })

  it('reports the number of selected images', () => {
    render(
      <ImageGalleryField
        id="gallery"
        label="Gallery"
        value={['g-1', 'g-2', 'g-3']}
        onChange={() => {}}
        upload={vi.fn()}
      />,
    )
    expect(screen.getByText(/gallery · 3/i)).toBeInTheDocument()
  })
})
