/**
 * Certificates — issuance from the review, member display/download, admin
 * management (email/revoke/download) and the public verification page.
 */

import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  adminDataHandlers,
  certificateAdminFixture,
  certificationDetailFixture,
  certificationListFixture,
  editorMeFixture,
  memberMeFixture,
  meFixture,
  publicCertificateFixture,
  publicCertificateWorkFixture,
} from './fixtures'
import { renderApp } from './helpers'
import type { HandlerMap } from './helpers'
import type { CertificateRef } from '../types/certificate'

const certificateRef: CertificateRef = {
  certificate_id: certificateAdminFixture.certificate_id,
  status: 'issued',
  issued_at: certificateAdminFixture.issued_at,
  email_status: 'sent',
  work_title: certificateAdminFixture.work_title,
  revoked_at: null,
}

const detailWithCertificate = {
  ...certificationDetailFixture,
  status: 'approved' as const,
  active: false,
  certificate: certificateRef,
}

const csrf = {
  '/api/auth/csrf': { body: { csrfToken: 'test-csrf' } },
  '/api/member/csrf': { body: { csrfToken: 'test-csrf' } },
}

const memberSession = (overrides: HandlerMap = {}): HandlerMap => ({
  ...csrf,
  '/api/member/me': { body: memberMeFixture },
  ...overrides,
})

const adminSession = (overrides: HandlerMap = {}): HandlerMap => ({
  ...csrf,
  '/api/auth/me': { body: meFixture },
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

describe('member certificate', () => {
  it('shows the certificate summary and downloads the member PDF', async () => {
    const { calls } = renderApp({
      entry: '/member/certifications',
      handlers: memberSession({
        '/api/member/certifications': { body: certificationListFixture() },
        '/api/member/certifications/cert-1': { body: detailWithCertificate },
        [`/api/member/certificates/${certificateAdminFixture.certificate_id}`]: {
          body: { ...certificateAdminFixture, download_path: `/member/certificates/${certificateAdminFixture.certificate_id}/download` },
        },
        [`/api/member/certificates/${certificateAdminFixture.certificate_id}/download`]: {
          raw: true,
          body: '%PDF-1.4 member',
          headers: { 'Content-Type': 'application/pdf' },
        },
      }),
    })

    fireEvent.click(await screen.findByRole('button', { name: /view details/i }))
    expect(await screen.findByText(certificateAdminFixture.certificate_id)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /download certificate/i }))
    await waitFor(() =>
      expect(
        calls.some(
          (c) =>
            c.url.includes(
              `/api/member/certificates/${certificateAdminFixture.certificate_id}/download`,
            ) && c.init?.method === 'GET',
        ),
      ).toBe(true),
    )
  })
})

describe('public certificate verification', () => {
  it('verifies an issued certificate', async () => {
    renderApp({
      entry: `/verify-certificate/${certificateAdminFixture.certificate_id}`,
      handlers: {
        [`/api/public/certificates/${certificateAdminFixture.certificate_id}`]: {
          body: publicCertificateFixture,
        },
      },
    })

    expect(await screen.findByText(/certificate verified/i)).toBeInTheDocument()
    expect(screen.getByText(publicCertificateFixture.member_name)).toBeInTheDocument()
    const workLink = screen.getByRole('link', { name: /embodied agents/i })
    expect(workLink).toHaveAttribute('href', publicCertificateFixture.work_url)
  })

  it('reports a revoked certificate with its reason', async () => {
    renderApp({
      entry: `/verify-certificate/${certificateAdminFixture.certificate_id}`,
      handlers: {
        [`/api/public/certificates/${certificateAdminFixture.certificate_id}`]: {
          body: {
            ...publicCertificateFixture,
            status: 'revoked',
            revoked_at: '2026-03-01T00:00:00Z',
            revocation_reason: 'Incorrect applicant details.',
          },
        },
      },
    })

    expect(await screen.findByText(/has been revoked/i)).toBeInTheDocument()
    expect(screen.getByText(/incorrect applicant details/i)).toBeInTheDocument()
  })

  it('treats an unknown certificate id as not found', async () => {
    renderApp({
      entry: '/verify-certificate/THL-CERT-2026-UNKNOWNXXXXXX',
      handlers: {
        '/api/public/certificates/THL-CERT-2026-UNKNOWNXXXXXX': {
          status: 404,
          body: { error: { code: 'CERTIFICATE_NOT_FOUND', message: 'Not found' } },
        },
      },
    })

    expect(await screen.findByText(/certificate not found/i)).toBeInTheDocument()
  })

  it('presents the certified work behind an issued certificate', async () => {
    renderApp({
      entry: `/verify-certificate/${certificateAdminFixture.certificate_id}`,
      handlers: {
        [`/api/public/certificates/${certificateAdminFixture.certificate_id}`]: {
          body: { ...publicCertificateFixture, work: publicCertificateWorkFixture },
        },
      },
    })

    expect(await screen.findByText(/the work behind this certificate/i)).toBeInTheDocument()
    expect(screen.getByText(/^certified version$/i)).toBeInTheDocument()
    expect(screen.getByText(publicCertificateWorkFixture.title)).toBeInTheDocument()
    expect(screen.getByText(/a study of embodied ai agents/i)).toBeInTheDocument()
    expect(screen.getByText(/an embodied ai experiment/i)).toBeInTheDocument()

    const author = screen.getByRole('link', { name: /ada lovelace/i })
    expect(author).toHaveAttribute('href', publicCertificateWorkFixture.member_profile_url)

    const external = screen.getAllByRole('link', { name: /repository/i })
    expect(external.length).toBeGreaterThan(0)
    for (const link of external) {
      expect(link).toHaveAttribute('href', 'https://github.com/example/embodied')
    }

    const project = screen.getByRole('link', { name: /view full project/i })
    expect(project).toHaveAttribute('href', publicCertificateWorkFixture.current_work_url)
    expect(project).toHaveAttribute('target', '_blank')
  })

  it('labels the current version when the work was edited after certification', async () => {
    renderApp({
      entry: `/verify-certificate/${certificateAdminFixture.certificate_id}`,
      handlers: {
        [`/api/public/certificates/${certificateAdminFixture.certificate_id}`]: {
          body: {
            ...publicCertificateFixture,
            work: { ...publicCertificateWorkFixture, has_newer_version: true },
          },
        },
      },
    })

    expect(await screen.findByText(/the work behind this certificate/i)).toBeInTheDocument()
    expect(screen.getByText(/updated since it was certified/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /view the current version/i })).toBeInTheDocument()
  })

  it('omits the certified work when none is publicly available', async () => {
    renderApp({
      entry: `/verify-certificate/${certificateAdminFixture.certificate_id}`,
      handlers: {
        [`/api/public/certificates/${certificateAdminFixture.certificate_id}`]: {
          body: publicCertificateFixture,
        },
      },
    })

    expect(await screen.findByText(/certificate verified/i)).toBeInTheDocument()
    expect(screen.queryByText(/the work behind this certificate/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/^certified version$/i)).not.toBeInTheDocument()
  })

  it('still shows the certified work for a revoked certificate', async () => {
    renderApp({
      entry: `/verify-certificate/${certificateAdminFixture.certificate_id}`,
      handlers: {
        [`/api/public/certificates/${certificateAdminFixture.certificate_id}`]: {
          body: {
            ...publicCertificateFixture,
            status: 'revoked',
            revoked_at: '2026-03-01T00:00:00Z',
            revocation_reason: 'Incorrect applicant details.',
            work: publicCertificateWorkFixture,
          },
        },
      },
    })

    expect(await screen.findByText(/has been revoked/i)).toBeInTheDocument()
    expect(screen.getByText(/the work behind this certificate/i)).toBeInTheDocument()
  })
})

describe('admin certificates', () => {
  it('lists issued certificates', async () => {
    renderApp({
      entry: '/admin/certificates',
      handlers: adminSession({
        '/api/admin/certificates': {
          body: { items: [certificateAdminFixture], total: 1, page: 1, page_size: 20, pages: 1 },
        },
      }),
    })

    expect(await screen.findByText(certificateAdminFixture.certificate_id)).toBeInTheDocument()
    expect(screen.getByText(/embodied agents/i)).toBeInTheDocument()
  })

  it('issues a certificate from an approved review', async () => {
    const { calls } = renderApp({
      entry: '/admin/certifications/cert-1',
      handlers: adminSession({
        '/api/admin/certifications/cert-1': {
          body: { ...certificationDetailFixture, status: 'approved', active: false },
        },
        '/api/admin/certificates': { body: certificateAdminFixture },
      }),
    })

    const issue = await screen.findByRole('button', { name: /approve & generate certificate/i })
    fireEvent.click(issue)

    await waitFor(() => {
      const post = calls.find(
        (c) => c.url.includes('/api/admin/certificates') && c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(String(post!.init?.body))).toMatchObject({ request_id: 'cert-1' })
    })
  })

  it('emails and revokes an existing certificate', async () => {
    const { calls } = renderApp({
      entry: '/admin/certifications/cert-1',
      handlers: adminSession({
        '/api/admin/certifications/cert-1': { body: detailWithCertificate },
        [`/api/admin/certificates/${certificateAdminFixture.certificate_id}`]: {
          body: certificateAdminFixture,
        },
        [`/api/admin/certificates/${certificateAdminFixture.certificate_id}/email`]: {
          body: {
            certificate_id: certificateAdminFixture.certificate_id,
            email_status: 'sent',
            email_sent_at: '2026-02-05T12:01:00Z',
            message: 'sent',
          },
        },
        [`/api/admin/certificates/${certificateAdminFixture.certificate_id}/revoke`]: {
          body: { ...certificateAdminFixture, status: 'revoked', revocation_reason: 'Mistake.' },
        },
      }),
    })

    fireEvent.click(await screen.findByRole('button', { name: /resend email/i }))
    await waitFor(() =>
      expect(
        calls.some(
          (c) =>
            c.url.includes(`/api/admin/certificates/${certificateAdminFixture.certificate_id}/email`) &&
            c.init?.method === 'POST',
        ),
      ).toBe(true),
    )

    fireEvent.click(screen.getByRole('button', { name: /^revoke$/i }))
    const reason = await screen.findByLabelText(/revocation reason/i)
    fireEvent.change(reason, { target: { value: 'Mistake.' } })
    fireEvent.click(screen.getByRole('button', { name: /confirm revocation/i }))

    await waitFor(() => {
      const post = calls.find(
        (c) =>
          c.url.includes(`/api/admin/certificates/${certificateAdminFixture.certificate_id}/revoke`) &&
          c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(String(post!.init?.body))).toMatchObject({ reason: 'Mistake.' })
    })
  })

  it('does not offer issuance to editors', async () => {
    renderApp({
      entry: '/admin/certifications/cert-1',
      handlers: adminSession({
        '/api/auth/me': { body: editorMeFixture },
        '/api/admin/certifications/cert-1': {
          body: { ...certificationDetailFixture, status: 'approved', active: false },
        },
      }),
    })

    expect(
      await screen.findByText(/only admins and owners can record certification decisions/i),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /approve & generate certificate/i }),
    ).not.toBeInTheDocument()
  })

  it('exposes a Certificates link in the admin sidebar', async () => {
    renderApp({ entry: '/admin', handlers: adminDataHandlers() })
    const links = await screen.findAllByRole('link', { name: 'Certificates' })
    expect(links.some((link) => link.getAttribute('href') === '/admin/certificates')).toBe(true)
  })
})
