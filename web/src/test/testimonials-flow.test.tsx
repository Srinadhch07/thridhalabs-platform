/** Public testimonial submission + admin moderation flow tests. */

import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { adminDataHandlers, emptyList, pendingTestimonialFixture } from './fixtures'
import { renderApp } from './helpers'

describe('public testimonial submission', () => {
  it('posts a new testimonial and shows the thank-you state', async () => {
    const { calls } = renderApp({
      entry: '/testimonials',
      handlers: {
        '/api/auth/csrf': { body: { csrfToken: 'test-csrf' } },
        '/api/public/testimonials': { body: { message: 'Thanks' } },
      },
    })

    fireEvent.change(await screen.findByLabelText(/^name/i), { target: { value: 'Grace Hopper' } })
    fireEvent.change(screen.getByLabelText(/testimonial$/i), { target: { value: 'Remarkable lab.' } })
    fireEvent.change(screen.getByLabelText(/rating/i), { target: { value: '5' } })
    fireEvent.click(screen.getByRole('button', { name: /submit testimonial/i }))

    expect(await screen.findByText(/thank you for sharing your experience/i)).toBeInTheDocument()

    await waitFor(() => {
      const post = calls.find((c) => c.url.includes('/api/public/testimonials') && c.init?.method === 'POST')
      expect(post).toBeTruthy()
      const body = JSON.parse(String(post!.init?.body))
      expect(body.person_name).toBe('Grace Hopper')
      expect(body.testimonial_text).toBe('Remarkable lab.')
      expect(body.rating).toBe(5)
      expect(body.status).toBeUndefined()
      expect(body.published).toBeUndefined()
    })
  })

  it('shows a maintenance notice when the server rejects the submission with 503', async () => {
    renderApp({
      entry: '/testimonials',
      handlers: {
        '/api/auth/csrf': { body: { csrfToken: 'test-csrf' } },
        '/api/public/testimonials': (_url, init) =>
          init?.method === 'POST'
            ? { status: 503, body: { error: { code: 'MAINTENANCE_MODE', message: 'Maintenance' } } }
            : { body: emptyList() },
      },
    })

    fireEvent.change(await screen.findByLabelText(/^name/i), { target: { value: 'Grace Hopper' } })
    fireEvent.change(screen.getByLabelText(/testimonial$/i), { target: { value: 'Remarkable lab.' } })
    fireEvent.click(screen.getByRole('button', { name: /submit testimonial/i }))

    expect(await screen.findByText(/offline for maintenance/i)).toBeInTheDocument()
    expect(screen.queryByText(/thank you for sharing your experience/i)).not.toBeInTheDocument()
  })
})

describe('admin testimonial moderation', () => {
  it('lists a status column and approves a pending submission', async () => {
    const { calls } = renderApp({
      entry: '/admin/testimonials',
      handlers: {
        ...adminDataHandlers(),
        '/api/testimonials': {
          body: { items: [pendingTestimonialFixture], total: 1, page: 1, page_size: 20, pages: 1 },
        },
      },
    })

    expect(await screen.findByText('Pending')).toBeInTheDocument()
    fireEvent.click(await screen.findByRole('button', { name: /approve/i }))

    await waitFor(() => {
      const patch = calls.find((c) => c.url.includes('/api/testimonials/t-pending') && c.init?.method === 'PATCH')
      expect(patch).toBeTruthy()
      const body = JSON.parse(String(patch!.init?.body))
      expect(body.status).toBe('approved')
    })
  })

  it('rejects a pending submission', async () => {
    const { calls } = renderApp({
      entry: '/admin/testimonials',
      handlers: {
        ...adminDataHandlers(),
        '/api/testimonials': {
          body: { items: [pendingTestimonialFixture], total: 1, page: 1, page_size: 20, pages: 1 },
        },
      },
    })

    expect(await screen.findByText('Pending')).toBeInTheDocument()
    fireEvent.click(await screen.findByRole('button', { name: /reject/i }))

    await waitFor(() => {
      const patch = calls.find((c) => c.url.includes('/api/testimonials/t-pending') && c.init?.method === 'PATCH')
      expect(patch).toBeTruthy()
      const body = JSON.parse(String(patch!.init?.body))
      expect(body.status).toBe('rejected')
    })
  })
})

describe('admin maintenance toggle', () => {
  it('requires confirmation before enabling maintenance', async () => {
    const { calls } = renderApp({ entry: '/admin/settings', handlers: adminDataHandlers() })
    await screen.findByLabelText(/site name/i)

    fireEvent.click(screen.getByRole('checkbox', { name: /maintenance mode/i }))

    expect(
      await screen.findByRole('heading', { name: /enable maintenance mode\?/i }),
    ).toBeInTheDocument()
    expect(
      screen.getAllByRole('button', { name: /enable maintenance/i }).length,
    ).toBeGreaterThan(0)

    const confirm = screen
      .getAllByRole('button', { name: /enable maintenance/i })
      .find((button) => button.textContent === 'Enable maintenance')
    fireEvent.click(confirm!)

    expect(await screen.findByText(/unsaved changes/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /save settings/i }))

    await waitFor(() => {
      const put = calls.find((c) => c.url.includes('/api/settings') && c.init?.method === 'PUT')
      expect(put).toBeTruthy()
      const body = JSON.parse(String(put!.init?.body))
      expect(body.maintenance_mode).toBe(true)
    })
  })

  it('does not enable maintenance when the confirm is cancelled', async () => {
    const { calls } = renderApp({ entry: '/admin/settings', handlers: adminDataHandlers() })
    await screen.findByLabelText(/site name/i)

    fireEvent.click(screen.getByRole('checkbox', { name: /maintenance mode/i }))
    const cancel = screen.getAllByRole('button', { name: /keep site live/i })[0]
    fireEvent.click(cancel)

    expect(screen.queryByText(/unsaved changes/i)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /save settings/i }))

    await waitFor(() => {
      const put = calls.find((c) => c.url.includes('/api/settings') && c.init?.method === 'PUT')
      expect(put).toBeTruthy()
      const body = JSON.parse(String(put!.init?.body))
      expect(body.maintenance_mode).toBe(false)
    })
  })
})