/**
 * Activity workspaces — the member's individual workspace for a programme or
 * hackathon (checklist, deliverable, progress updates) and the admin review
 * queue for those individual submissions.
 */

import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import {
  activityDeliverableFixture,
  activityProgressUpdateFixture,
  activityWorkspaceFixture,
  activityWorkspaceListFixture,
  adminActivityFixture,
  adminActivitySubmissionFixture,
  emptyActivityWorkspaceFixture,
  memberMeFixture,
  meFixture,
} from './fixtures'
import { renderApp } from './helpers'
import type { HandlerMap } from './helpers'
import type { AdminActivitySubmission } from '../types/activitySubmission'

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

const workspaceHandlers = (extra: HandlerMap = {}): HandlerMap =>
  memberSession({
    '/api/member/activity-workspaces': { body: activityWorkspaceListFixture() },
    '/api/member/activity-workspaces/ai-builders-programme-2026': {
      body: activityWorkspaceFixture,
    },
    ...extra,
  })

describe('member my activities', () => {
  it('lists the workspaces the member has joined with their progress', async () => {
    renderApp({
      entry: '/member/activities',
      handlers: workspaceHandlers({
        '/api/member/activities': { body: { items: [] } },
      }),
    })

    const link = await screen.findByRole('link', { name: 'Open workspace' })
    expect(link).toHaveAttribute('href', '/member/activities/ai-builders-programme-2026')
    expect(screen.getByRole('heading', { name: 'AI Builders Programme 2026' })).toBeInTheDocument()
    expect(screen.getByText('1 / 2 tasks · 50%')).toBeInTheDocument()
  })

  it('shows an empty state when the member has no workspaces', async () => {
    renderApp({
      entry: '/member/activities',
      handlers: workspaceHandlers({
        '/api/member/activity-workspaces': { body: { items: [] } },
        '/api/member/activities': { body: { items: [] } },
      }),
    })

    expect(await screen.findByText(/no workspaces yet/i)).toBeInTheDocument()
  })
})

describe('member activity workspace', () => {
  it('shows the activity content, checklist and the member own submissions', async () => {
    renderApp({
      entry: '/member/activities/ai-builders-programme-2026',
      handlers: workspaceHandlers(),
    })

    expect(
      await screen.findByRole('heading', { name: 'AI Builders Programme 2026' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Ship a working prototype')).toBeInTheDocument()
    expect(screen.getByText('Work independently — participation is individual.')).toBeInTheDocument()
    expect(screen.getByText('A public repository')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'https://github.com/thridhalabs/starter' })).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Build the prototype' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'Write the report' })).not.toBeChecked()
    expect(screen.getByText('1 / 2 tasks · 50%')).toBeInTheDocument()
    expect(screen.getByText(activityDeliverableFixture.description)).toBeInTheDocument()
    expect(screen.getByText(activityProgressUpdateFixture.description)).toBeInTheDocument()
  })

  it('marks a personal task complete', async () => {
    const { calls } = renderApp({
      entry: '/member/activities/ai-builders-programme-2026',
      handlers: workspaceHandlers(),
    })

    fireEvent.click(await screen.findByRole('checkbox', { name: 'Write the report' }))

    await waitFor(() => {
      const patch = calls.find(
        (c) =>
          c.url.includes('/api/member/activity-workspaces/ai-builders-programme-2026/tasks') &&
          c.init?.method === 'PATCH',
      )
      expect(patch).toBeTruthy()
      expect(JSON.parse(String(patch!.init?.body))).toMatchObject({
        task_id: 'task-2',
        completed: true,
      })
    })
  })

  it('posts a progress update', async () => {
    const created = { ...activityProgressUpdateFixture, description: 'Wired the sensor pipeline.' }
    const { calls } = renderApp({
      entry: '/member/activities/ai-builders-programme-2026',
      handlers: workspaceHandlers({
        '/api/member/activity-submissions': (_url, init) =>
          init?.method === 'POST'
            ? { status: 201, body: created }
            : { body: { items: [], total: 0, page: 1, page_size: 20, pages: 0 } },
      }),
    })

    fireEvent.click(await screen.findByRole('button', { name: 'Post an update' }))
    fireEvent.change(await screen.findByLabelText(/what did you work on\?/i), {
      target: { value: 'Wired the sensor pipeline.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Post update' }))

    await waitFor(() => {
      const post = calls.find(
        (c) => c.url.includes('/api/member/activity-submissions') && c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(String(post!.init?.body))).toMatchObject({
        activity_id: 'a-1',
        kind: 'progress_update',
        description: 'Wired the sensor pipeline.',
      })
    })
  })

  it('blocks a progress update with no description', async () => {
    const { calls } = renderApp({
      entry: '/member/activities/ai-builders-programme-2026',
      handlers: workspaceHandlers(),
    })

    fireEvent.click(await screen.findByRole('button', { name: 'Post an update' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Post update' }))

    expect(await screen.findByText(/description is required/i)).toBeInTheDocument()
    expect(calls.some((c) => c.init?.method === 'POST')).toBe(false)
  })

  it('requires the repository URL when the activity asks for one', async () => {
    const { calls } = renderApp({
      entry: '/member/activities/ai-builders-programme-2026',
      handlers: workspaceHandlers({
        '/api/member/activity-workspaces/ai-builders-programme-2026': {
          body: emptyActivityWorkspaceFixture,
        },
      }),
    })

    fireEvent.change(await screen.findByLabelText(/^description/i), {
      target: { value: 'A short write-up of my project.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Submit deliverable' }))

    expect(await screen.findByText(/requires a repository url/i)).toBeInTheDocument()
    expect(calls.some((c) => c.init?.method === 'POST')).toBe(false)
  })

  it('edits and resubmits the deliverable', async () => {
    const resubmitted = { ...activityDeliverableFixture, version: 2 }
    const { calls } = renderApp({
      entry: '/member/activities/ai-builders-programme-2026',
      handlers: workspaceHandlers({
        '/api/member/activity-submissions/sub-deliverable-1': (_url, init) =>
          init?.method === 'PATCH' ? { body: resubmitted } : { body: activityDeliverableFixture },
      }),
    })

    const editButtons = await screen.findAllByRole('button', { name: 'Edit & resubmit' })
    fireEvent.click(editButtons[0])
    fireEvent.change(await screen.findByLabelText(/^description/i), {
      target: { value: 'Revised: added the evaluation harness.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Resubmit for review' }))

    await waitFor(() => {
      const patch = calls.find(
        (c) =>
          c.url.includes('/api/member/activity-submissions/sub-deliverable-1') &&
          c.init?.method === 'PATCH',
      )
      expect(patch).toBeTruthy()
      expect(JSON.parse(String(patch!.init?.body))).toMatchObject({
        description: 'Revised: added the evaluation harness.',
      })
    })
  })

  it('explains why the deliverable cannot be submitted yet', async () => {
    renderApp({
      entry: '/member/activities/ai-builders-programme-2026',
      handlers: workspaceHandlers({
        '/api/member/activity-workspaces/ai-builders-programme-2026': {
          body: {
            ...emptyActivityWorkspaceFixture,
            can_submit: false,
            submit_blocked_reason: 'Submissions closed on 28 March 2026.',
          },
        },
      }),
    })

    expect(await screen.findByText('Deliverable not available')).toBeInTheDocument()
    expect(screen.getByText('Submissions closed on 28 March 2026.')).toBeInTheDocument()
  })
})

describe('admin activity submission review', () => {
  const panelHandlers = (extra: HandlerMap = {}): HandlerMap =>
    adminSession({
      '/api/admin/activities/a-1': { body: adminActivityFixture },
      '/api/admin/activity-submissions/activity/a-1': {
        body: {
          items: [adminActivitySubmissionFixture],
          total: 1,
          page: 1,
          page_size: 20,
          pages: 1,
        },
      },
      ...extra,
    })

  it('lists the individual submissions of the activity', async () => {
    renderApp({
      entry: '/admin/activities/a-1',
      handlers: panelHandlers(),
    })

    expect(await screen.findByText('Ada Lovelace')).toBeInTheDocument()
    expect(screen.getByText(/THL-M-2026-0001/)).toBeInTheDocument()
    expect(screen.getAllByText('Deliverable').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Awaiting review').length).toBeGreaterThan(0)
  })

  it('approves a submission', async () => {
    const approved: AdminActivitySubmission = {
      ...adminActivitySubmissionFixture,
      status: 'approved',
    }
    const { calls } = renderApp({
      entry: '/admin/activities/a-1',
      handlers: panelHandlers({
        '/api/admin/activity-submissions/sub-deliverable-1/decision': { body: approved },
      }),
    })

    fireEvent.click(await screen.findByRole('button', { name: 'Record decision' }))

    await waitFor(() => {
      const post = calls.find(
        (c) =>
          c.url.includes(
            '/api/admin/activity-submissions/sub-deliverable-1/decision',
          ) && c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(String(post!.init?.body))).toMatchObject({ action: 'approve' })
    })
  })

  it('sends feedback when requesting changes', async () => {
    const changed: AdminActivitySubmission = {
      ...adminActivitySubmissionFixture,
      status: 'changes_requested',
    }
    const { calls } = renderApp({
      entry: '/admin/activities/a-1',
      handlers: panelHandlers({
        '/api/admin/activity-submissions/sub-deliverable-1/decision': { body: changed },
      }),
    })

    fireEvent.change(await screen.findByLabelText('Filter submissions by status'), {
      target: { value: 'pending' },
    })
    const select = screen
      .getAllByLabelText(/^decision for/i)
      .find((element) => element.tagName === 'SELECT') as HTMLSelectElement
    fireEvent.change(select, { target: { value: 'request_changes' } })
    fireEvent.change(screen.getByLabelText(/^feedback for/i), {
      target: { value: 'Please link the evaluation harness.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Record decision' }))

    await waitFor(() => {
      const post = calls.find(
        (c) =>
          c.url.includes(
            '/api/admin/activity-submissions/sub-deliverable-1/decision',
          ) && c.init?.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(String(post!.init?.body))).toMatchObject({
        action: 'request_changes',
        feedback: 'Please link the evaluation harness.',
      })
    })
  })

  it('does not offer a decision on a finalised submission', async () => {
    renderApp({
      entry: '/admin/activities/a-1',
      handlers: panelHandlers({
        '/api/admin/activity-submissions/activity/a-1': {
          body: {
            items: [{ ...adminActivitySubmissionFixture, status: 'approved' }],
            total: 1,
            page: 1,
            page_size: 20,
            pages: 1,
          },
        },
      }),
    })

    expect(await screen.findByText(/this submission is final/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Record decision' })).not.toBeInTheDocument()
  })
})
