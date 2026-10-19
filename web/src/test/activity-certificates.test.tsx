/**
 * Activity certificates — public verification and the admin management page
 * (listing, eligibility-driven issuance, email and revoke).
 */

import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { adminActivitiesFixture, meFixture } from './fixtures'
import { renderApp } from './helpers'
import type { HandlerMap } from './helpers'
import type {
  ActivityCertificateAdmin,
  ActivityCertificateBulkResult,
  ActivityCertificateEligibleList,
  PublicActivityCertificate,
} from '../types/activityCertificate'

const CERT_ID = 'THL-ACT-CERT-2026-ABCDEFGHJKLM'

const adminFixture: ActivityCertificateAdmin = {
  certificate_id: CERT_ID,
  activity_id: 'a-1',
  activity_title: 'AI Builders Programme 2026',
  activity_slug: 'ai-builders-programme-2026',
  activity_type: 'programme',
  award_category: 'participation',
  award_label: 'Participation',
  award_statement: 'For active and valued participation.',
  member_id: 'member-1',
  member_readable_id: 'MEM-0001',
  member_name: 'Ada Lovelace',
  work_id: null,
  work_title: null,
  status: 'issued',
  issued_at: '2026-03-02T00:00:00Z',
  revoked_at: null,
  revocation_reason: null,
  email_status: 'not_sent',
  email_sent_at: null,
  pdf_filename: `ThridhaLabs-Activity-Certificate-${CERT_ID}.pdf`,
  pdf_size_bytes: 12345,
  verify_url: `https://thridhalabs.test/verify-activity-certificate/${CERT_ID}`,
  download_path: `/admin/activity-certificates/${CERT_ID}/download`,
  issued_by: 'Ada Lovelace',
  issued_by_role: 'owner',
  template_version: '1',
  email_attempts: 0,
  email_last_error: null,
}

const publicFixture: PublicActivityCertificate = {
  certificate_id: CERT_ID,
  status: 'issued',
  issued_at: '2026-03-02T00:00:00Z',
  member_name: 'Ada Lovelace',
  activity_title: 'AI Builders Programme 2026',
  activity_type: 'programme',
  award_category: 'first_place',
  award_label: 'First place',
  award_statement: 'For outstanding performance.',
  work: null,
  revoked_at: null,
  revocation_reason: null,
}

const eligibleFixture: ActivityCertificateEligibleList = {
  activity_id: 'a-1',
  activity_title: 'AI Builders Programme 2026',
  items: [
    {
      member_id: 'member-1',
      member_readable_id: 'MEM-0001',
      member_name: 'Ada Lovelace',
      member_email: 'ada@example.com',
      participation_status: 'confirmed',
      role: 'AI Engineer',
      already_issued_awards: [],
    },
  ],
}

const bulkResultFixture: ActivityCertificateBulkResult = {
  issued: [adminFixture],
  skipped: [],
  failed: [],
  issued_count: 1,
  skipped_count: 0,
  failed_count: 0,
}

const csrf = {
  '/api/auth/csrf': { body: { csrfToken: 'test-csrf' } },
  '/api/member/csrf': { body: { csrfToken: 'test-csrf' } },
}

const adminSession = (overrides: HandlerMap = {}): HandlerMap => ({
  ...csrf,
  '/api/auth/me': { body: meFixture },
  '/api/admin/activities': { body: adminActivitiesFixture() },
  ...overrides,
})

let anchorClick: ReturnType<typeof vi.spyOn> | null = null

beforeEach(() => {
  if (typeof URL.createObjectURL !== 'function') {
    ;(URL as unknown as { createObjectURL: () => string }).createObjectURL = () => 'blob:mock'
  }
  if (typeof URL.revokeObjectURL !== 'function') {
    ;(URL as unknown as { revokeObjectURL: () => void }).revokeObjectURL = () => undefined
  }
  anchorClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
})

afterEach(() => {
  anchorClick?.mockRestore()
  vi.restoreAllMocks()
})

describe('public activity certificate verification', () => {
  it('verifies an issued certificate', async () => {
    renderApp({
      entry: `/verify-activity-certificate/${CERT_ID}`,
      handlers: { [`/api/public/activity-certificates/${CERT_ID}`]: { body: publicFixture } },
    })

    expect(await screen.findByText(/certificate verified/i)).toBeInTheDocument()
    expect(screen.getByText(publicFixture.member_name)).toBeInTheDocument()
    expect(screen.getByText(/ai builders programme 2026/i)).toBeInTheDocument()
    expect(screen.getByText('First place')).toBeInTheDocument()
  })

  it('links the recognized work when it is public', async () => {
    renderApp({
      entry: `/verify-activity-certificate/${CERT_ID}`,
      handlers: {
        [`/api/public/activity-certificates/${CERT_ID}`]: {
          body: {
            ...publicFixture,
            work: { title: 'Embodied Agents', url: 'https://thridhalabs.test/members/ada/works/embodied' },
          },
        },
      },
    })

    const link = await screen.findByRole('link', { name: /embodied agents/i })
    expect(link).toHaveAttribute('href', 'https://thridhalabs.test/members/ada/works/embodied')
  })

  it('reports a revoked certificate with its reason', async () => {
    renderApp({
      entry: `/verify-activity-certificate/${CERT_ID}`,
      handlers: {
        [`/api/public/activity-certificates/${CERT_ID}`]: {
          body: {
            ...publicFixture,
            status: 'revoked',
            revoked_at: '2026-03-10T00:00:00Z',
            revocation_reason: 'Issued in error.',
          },
        },
      },
    })

    expect(await screen.findByText(/has been revoked/i)).toBeInTheDocument()
    expect(screen.getByText(/issued in error/i)).toBeInTheDocument()
  })

  it('treats an unknown certificate id as not found', async () => {
    renderApp({
      entry: '/verify-activity-certificate/THL-ACT-CERT-2026-UNKNOWNXXXXXX',
      handlers: {
        '/api/public/activity-certificates/THL-ACT-CERT-2026-UNKNOWNXXXXXX': {
          status: 404,
          body: { error: { code: 'ACTIVITY_CERTIFICATE_NOT_FOUND', message: 'Not found' } },
        },
      },
    })

    expect(await screen.findByText(/certificate not found/i)).toBeInTheDocument()
  })
})

describe('admin activity certificates', () => {
  it('lists issued activity certificates', async () => {
    renderApp({
      entry: '/admin/activity-certificates',
      handlers: adminSession({
        '/api/admin/activity-certificates': {
          body: { items: [adminFixture], total: 1, page: 1, page_size: 20, pages: 1 },
        },
      }),
    })

    expect(await screen.findByText(CERT_ID)).toBeInTheDocument()
    expect(screen.getByText('AI Builders Programme 2026')).toBeInTheDocument()
    expect(screen.getAllByText('Participation').length).toBeGreaterThan(0)
  })

  it('issues to a selected eligible participant', async () => {
    const { calls } = renderApp({
      entry: '/admin/activity-certificates',
      handlers: adminSession({
        '/api/admin/activity-certificates': {
          body: { items: [], total: 0, page: 1, page_size: 20, pages: 1 },
        },
        '/api/admin/activity-certificates/eligible': { body: eligibleFixture },
        '/api/admin/activity-certificates/bulk': { body: bulkResultFixture },
      }),
    })

    const activitySelect = await screen.findByLabelText('Activity')
    await screen.findByRole('option', { name: /ai builders programme 2026/i })
    fireEvent.change(activitySelect, { target: { value: 'a-1' } })

    const checkbox = await screen.findByLabelText(/select ada lovelace/i)
    fireEvent.click(checkbox)

    fireEvent.click(screen.getByRole('button', { name: /issue selected \(1\)/i }))

    await waitFor(() => {
      const post = calls.find(
        (c) =>
          c.url.includes('/api/admin/activity-certificates/bulk') &&
          c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(String(post!.init?.body))).toMatchObject({
        activity_id: 'a-1',
        award_category: 'participation',
        recipients: [{ member_id: 'member-1' }],
      })
    })
  })

  it('emails and revokes an issued certificate', async () => {
    const { calls } = renderApp({
      entry: '/admin/activity-certificates',
      handlers: adminSession({
        '/api/admin/activity-certificates': {
          body: { items: [adminFixture], total: 1, page: 1, page_size: 20, pages: 1 },
        },
        [`/api/admin/activity-certificates/${CERT_ID}/email`]: {
          body: {
            certificate_id: CERT_ID,
            email_status: 'sent',
            email_sent_at: '2026-03-03T00:00:00Z',
            message: 'sent',
          },
        },
        [`/api/admin/activity-certificates/${CERT_ID}/revoke`]: {
          body: { ...adminFixture, status: 'revoked', revocation_reason: 'Mistake.' },
        },
      }),
    })

    fireEvent.click(await screen.findByRole('button', { name: /^email$/i }))
    await waitFor(() =>
      expect(
        calls.some(
          (c) =>
            c.url.includes(`/api/admin/activity-certificates/${CERT_ID}/email`) &&
            c.init?.method === 'POST',
        ),
      ).toBe(true),
    )

    fireEvent.click(screen.getByRole('button', { name: /^revoke$/i }))
    fireEvent.change(await screen.findByLabelText(/revocation reason/i), {
      target: { value: 'Issued in error.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^confirm$/i }))

    await waitFor(() => {
      const post = calls.find(
        (c) =>
          c.url.includes(`/api/admin/activity-certificates/${CERT_ID}/revoke`) &&
          c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(String(post!.init?.body))).toMatchObject({ reason: 'Issued in error.' })
    })
  })

  it('exposes an Activity certificates link in the admin sidebar', async () => {
    renderApp({ entry: '/admin/activity-certificates', handlers: adminSession() })
    const links = await screen.findAllByRole('link', { name: 'Activity certificates' })
    expect(
      links.some((link) => link.getAttribute('href') === '/admin/activity-certificates'),
    ).toBe(true)
  })
})
