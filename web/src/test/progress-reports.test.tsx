/**
 * Project Progress Reports — member projects & report authoring, the private
 * contribution history, and the admin review queue with approve / request-changes
 * decisions.
 */

import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import {
  adminReportFixture,
  adminReportListFixture,
  approvedReportFixture,
  changesRequestedReportFixture,
  contributionHistoryFixture,
  memberMeFixture,
  memberProjectsFixture,
  memberReportFixture,
  meFixture,
  reportListFixture,
} from './fixtures'
import { renderApp } from './helpers'
import type { HandlerMap } from './helpers'
import type { AdminReport, MemberReport } from '../types/report'

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

/** Member reports: GET returns the list, POST/PATCH return the mutated report. */
const memberReportsHandlers = (
  list: ReturnType<typeof reportListFixture>,
  created: MemberReport,
): HandlerMap => ({
  '/api/member/reports': (_url, init) =>
    init?.method === 'POST' ? { status: 201, body: created } : { body: list },
  '/api/member/reports/r-1': (_url, init) =>
    init?.method === 'PATCH' ? { body: created } : { body: created },
})

const projectReportsHandlers = (
  extra: HandlerMap = {},
): HandlerMap =>
  memberSession({
    '/api/member/reports/projects': { body: memberProjectsFixture() },
    ...memberReportsHandlers(reportListFixture([memberReportFixture]), memberReportFixture),
    ...extra,
  })

describe('member my projects', () => {
  it('lists a confirmed project with its report roll-up', async () => {
    renderApp({
      entry: '/member/projects',
      handlers: memberSession({
        '/api/member/reports/projects': { body: memberProjectsFixture() },
      }),
    })

    const link = await screen.findByRole('link', { name: 'Open reports' })
    expect(link).toHaveAttribute('href', '/member/projects/a-project-1')
    expect(screen.getByRole('heading', { name: 'Embodied Agents' })).toBeInTheDocument()
    expect(screen.getByText('3 reports')).toBeInTheDocument()
    expect(screen.getByText('1 awaiting review')).toBeInTheDocument()
    expect(screen.getByText('1 changes requested')).toBeInTheDocument()
    expect(screen.getByText('1 approved')).toBeInTheDocument()
    expect(screen.getByText('Role: AI Engineer')).toBeInTheDocument()
  })

  it('shows an empty state when the member has no projects', async () => {
    renderApp({
      entry: '/member/projects',
      handlers: memberSession({
        '/api/member/reports/projects': { body: { items: [] } },
      }),
    })

    expect(await screen.findByText(/no projects yet/i)).toBeInTheDocument()
  })
})

describe('member report authoring', () => {
  it('submits a progress report with description and evidence link', async () => {
    const created: MemberReport = {
      ...memberReportFixture,
      description: 'Wrote the rollout script.',
    }
    const { calls } = renderApp({
      entry: '/member/projects/a-project-1',
      handlers: projectReportsHandlers({
        '/api/member/reports': (_url, init) =>
          init?.method === 'POST'
            ? { status: 201, body: created }
            : { body: reportListFixture([memberReportFixture]) },
      }),
    })

    fireEvent.change(await screen.findByLabelText(/what did you work on\?/i), {
      target: { value: 'Wrote the rollout script.' },
    })
    fireEvent.change(screen.getByLabelText('Evidence links'), {
      target: { value: 'https://github.com/example/run' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Submit report' }))

    await waitFor(() => {
      const post = calls.find(
        (c) => c.url.includes('/api/member/reports') && c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(String(post!.init?.body))).toMatchObject({
        activity_id: 'a-project-1',
        description: 'Wrote the rollout script.',
        evidence_links: ['https://github.com/example/run'],
      })
      expect(JSON.parse(String(post!.init?.body)).client_request_id).toBeTruthy()
    })

    expect(await screen.findByText('Report submitted for review.')).toBeInTheDocument()
  })

  it('blocks a submit with no description', async () => {
    const { calls } = renderApp({
      entry: '/member/projects/a-project-1',
      handlers: projectReportsHandlers(),
    })

    fireEvent.click(await screen.findByRole('button', { name: 'Submit report' }))

    expect(await screen.findByText(/short description is required/i)).toBeInTheDocument()
    expect(calls.some((c) => c.init?.method === 'POST')).toBe(false)
  })

  it('edits and resubmits a report while it is not finalised', async () => {
    const resubmitted: MemberReport = {
      ...memberReportFixture,
      description: 'Revised: linked the run log.',
      version: 2,
    }
    const { calls } = renderApp({
      entry: '/member/projects/a-project-1',
      handlers: projectReportsHandlers({
        '/api/member/reports/r-1': (_url, init) =>
          init?.method === 'PATCH'
            ? { body: resubmitted }
            : { body: memberReportFixture },
      }),
    })

    fireEvent.click(await screen.findByRole('button', { name: 'Edit & resubmit' }))
    fireEvent.change(await screen.findByLabelText(/what changed in this update\?/i), {
      target: { value: 'Revised: linked the run log.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Resubmit for review' }))

    await waitFor(() => {
      const patch = calls.find(
        (c) => c.url.includes('/api/member/reports/r-1') && c.init?.method === 'PATCH',
      )
      expect(patch).toBeTruthy()
      expect(JSON.parse(String(patch!.init?.body))).toMatchObject({
        description: 'Revised: linked the run log.',
      })
    })
  })

  it('surfaces reviewer feedback on a changes-requested report', async () => {
    renderApp({
      entry: '/member/projects/a-project-1',
      handlers: projectReportsHandlers({
        '/api/member/reports': { body: reportListFixture([changesRequestedReportFixture]) },
      }),
    })

    expect(
      await screen.findByText(/reviewer feedback: please link the run log/i),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Edit & resubmit' })).toBeInTheDocument()
    expect(screen.getAllByText('Changes requested').length).toBeGreaterThan(0)
  })

  it('hides the edit action for an approved report', async () => {
    renderApp({
      entry: '/member/projects/a-project-1',
      handlers: projectReportsHandlers({
        '/api/member/reports': { body: reportListFixture([approvedReportFixture]) },
      }),
    })

    expect(
      await screen.findByText(/completed the sensor-fusion milestone/i),
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit & resubmit' })).not.toBeInTheDocument()
    expect(screen.getAllByText('Approved').length).toBeGreaterThan(0)
  })
})

describe('member contribution history', () => {
  it('lists approved reports grouped by project, privately', async () => {
    renderApp({
      entry: '/member/contributions',
      handlers: memberSession({
        '/api/member/reports/contributions': { body: contributionHistoryFixture },
      }),
    })

    expect(
      await screen.findByRole('heading', { name: 'Contribution history' }),
    ).toBeInTheDocument()
    expect(
      await screen.findByRole('heading', { name: 'Embodied Agents' }),
    ).toBeInTheDocument()
    expect(screen.getByText(/completed the sensor-fusion milestone/i)).toBeInTheDocument()
    expect(screen.getByText(/1 approved report across 1 project/i)).toBeInTheDocument()
    expect(screen.getByText(/never published automatically/i)).toBeInTheDocument()
  })

  it('shows an empty state when nothing has been approved yet', async () => {
    renderApp({
      entry: '/member/contributions',
      handlers: memberSession({
        '/api/member/reports/contributions': { body: { items: [], total_reports: 0 } },
      }),
    })

    expect(await screen.findByText(/no approved reports yet/i)).toBeInTheDocument()
  })
})

describe('admin review queue', () => {
  it('lists reports awaiting review by default', async () => {
    const { calls } = renderApp({
      entry: '/admin/reports',
      handlers: adminSession({
        '/api/admin/reports': { body: adminReportListFixture() },
      }),
    })

    const link = await screen.findByRole('link', { name: 'Embodied Agents' })
    expect(link).toHaveAttribute('href', '/admin/reports/r-1')

    const table = screen.getByRole('table')
    expect(within(table).getByText('Ada Lovelace')).toBeInTheDocument()
    expect(within(table).getByText('THL-M-2026-0001')).toBeInTheDocument()
    expect(within(table).getByText('Awaiting review')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Review' })).toHaveAttribute(
      'href',
      '/admin/reports/r-1',
    )

    await waitFor(() =>
      expect(
        calls.some(
          (c) => c.url.includes('/api/admin/reports') && c.url.includes('status=pending'),
        ),
      ).toBe(true),
    )
  })

  it('searches the queue by member or project', async () => {
    const { calls } = renderApp({
      entry: '/admin/reports',
      handlers: adminSession({
        '/api/admin/reports': { body: adminReportListFixture() },
      }),
    })

    const input = await screen.findByLabelText('Search reports')
    fireEvent.change(input, { target: { value: 'ada' } })
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))

    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes('/api/admin/reports') && c.url.includes('search=ada')),
      ).toBe(true),
    )
  })

  it('filters the queue by status', async () => {
    const { calls } = renderApp({
      entry: '/admin/reports',
      handlers: adminSession({
        '/api/admin/reports': { body: adminReportListFixture() },
      }),
    })

    const select = await screen.findByLabelText('Filter by status')
    fireEvent.change(select, { target: { value: 'approved' } })

    await waitFor(() =>
      expect(
        calls.some(
          (c) => c.url.includes('/api/admin/reports') && c.url.includes('status=approved'),
        ),
      ).toBe(true),
    )
  })
})

describe('admin review decisions', () => {
  const detailHandlers = (extra: HandlerMap = {}): HandlerMap =>
    adminSession({
      '/api/admin/reports/r-1': { body: adminReportFixture },
      ...extra,
    })

  it('approves a report through the review detail', async () => {
    const approved: AdminReport = { ...adminReportFixture, status: 'approved' }
    const { calls } = renderApp({
      entry: '/admin/reports/r-1',
      handlers: detailHandlers({
        '/api/admin/reports/r-1/decision': { body: approved },
      }),
    })

    fireEvent.click(await screen.findByRole('radio', { name: 'Approve' }))
    fireEvent.click(screen.getByRole('button', { name: 'Submit decision' }))

    await waitFor(() => {
      const post = calls.find(
        (c) =>
          c.url.includes('/api/admin/reports/r-1/decision') && c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(String(post!.init?.body))).toMatchObject({ action: 'approve' })
    })
  })

  it('requires feedback when requesting changes', async () => {
    const { calls } = renderApp({
      entry: '/admin/reports/r-1',
      handlers: detailHandlers(),
    })

    fireEvent.click(await screen.findByRole('radio', { name: 'Request changes' }))
    fireEvent.click(screen.getByRole('button', { name: 'Submit decision' }))

    expect(
      await screen.findByText(/feedback is required when requesting changes/i),
    ).toBeInTheDocument()
    expect(calls.some((c) => c.url.includes('/decision') && c.init?.method === 'POST')).toBe(
      false,
    )
  })

  it('submits requested changes with feedback', async () => {
    const changed: AdminReport = { ...adminReportFixture, status: 'changes_requested' }
    const { calls } = renderApp({
      entry: '/admin/reports/r-1',
      handlers: detailHandlers({
        '/api/admin/reports/r-1/decision': { body: changed },
      }),
    })

    fireEvent.click(await screen.findByRole('radio', { name: 'Request changes' }))
    fireEvent.change(screen.getByLabelText('Feedback'), {
      target: { value: 'Please link the run log.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Submit decision' }))

    await waitFor(() => {
      const post = calls.find(
        (c) =>
          c.url.includes('/api/admin/reports/r-1/decision') && c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(String(post!.init?.body))).toMatchObject({
        action: 'request_changes',
        feedback: 'Please link the run log.',
      })
    })
  })

  it('does not offer decisions for an approved report', async () => {
    renderApp({
      entry: '/admin/reports/r-1',
      handlers: detailHandlers({
        '/api/admin/reports/r-1': {
          body: { ...adminReportFixture, status: 'approved', review_feedback: null },
        },
      }),
    })

    expect(await screen.findByText(/not awaiting review/i)).toBeInTheDocument()
    expect(screen.queryByRole('radio', { name: 'Approve' })).not.toBeInTheDocument()
  })
})
