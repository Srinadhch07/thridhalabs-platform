/**
 * Admin AI Summaries page regression tests.
 *
 * These cover the confirmed glitches on `/admin/ai/summaries`:
 *  - a spurious error state before any summary exists (missing-id request),
 *  - a stale member selection when switching projects,
 *  - a stale summary card after generating for a new target,
 *  - Publish being enabled before the draft has been reviewed/saved.
 */

import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { adminDataHandlers, aiSourceOverviewFixture, aiSummaryFixture } from './fixtures'
import { renderApp } from './helpers'

const ENTRY = '/admin/ai/summaries'

function summaryCard(): HTMLElement {
  const heading = screen.getByRole('heading', { level: 3, name: /^summary$/i })
  return heading.closest('.member-card') as HTMLElement
}

async function selectProject(value: string): Promise<void> {
  const project = (await screen.findByLabelText('Project (Activity)')) as HTMLSelectElement
  // Options arrive with the sources request; jsdom ignores a value without a match.
  await waitFor(() => expect(project.querySelector(`option[value="${value}"]`)).not.toBeNull())
  fireEvent.change(project, { target: { value } })
}

function memberSelect(): HTMLSelectElement {
  return screen.getByLabelText('Member') as HTMLSelectElement
}

describe('admin AI summaries page', () => {
  it('does not show a spurious error state before a summary is generated', async () => {
    renderApp({
      entry: ENTRY,
      handlers: {
        ...adminDataHandlers(),
        '/api/admin/ai/sources': { body: aiSourceOverviewFixture },
      },
    })

    expect(
      await screen.findByRole('heading', { level: 1, name: /ai summaries/i }),
    ).toBeInTheDocument()
    // Sources loaded and the picker is ready.
    await screen.findByRole('option', { name: /atlas engine/i })
    await waitFor(() => expect(screen.queryByLabelText('Member')).toBeInTheDocument())

    // No summary has been generated yet, so no error banner should appear.
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('resets the member selection when the project changes', async () => {
    const { calls } = renderApp({
      entry: ENTRY,
      handlers: {
        ...adminDataHandlers(),
        '/api/admin/ai/sources': { body: aiSourceOverviewFixture },
        // The request body is what matters: a stale member id would 409 here.
        '/api/admin/ai/summaries/generate': {
          status: 409,
          body: { error: { code: 'AI_NO_APPROVED_REPORTS', message: 'no eligible reports' } },
        },
      },
    })

    await selectProject('act-1')
    await waitFor(() => expect(memberSelect().value).toBe('member-1'))

    await selectProject('act-2')
    await waitFor(() => expect(memberSelect().value).toBe('member-2'))

    fireEvent.click(screen.getByRole('button', { name: /generate summary/i }))
    await waitFor(() => {
      expect(calls.some((call) => call.url.includes('/admin/ai/summaries/generate'))).toBe(true)
    })
    const generateCall = calls.find((call) => call.url.includes('/admin/ai/summaries/generate'))
    const body = JSON.parse(String(generateCall?.init?.body))
    expect(body).toEqual({ activity_id: 'act-2', member_id: 'member-2' })
  })

  it('shows the newly generated summary even when the refresh request fails', async () => {
    let generateCount = 0
    renderApp({
      entry: ENTRY,
      handlers: {
        ...adminDataHandlers(),
        '/api/admin/ai/sources': { body: aiSourceOverviewFixture },
        '/api/admin/ai/summaries/generate': () => {
          generateCount += 1
          return {
            body:
              generateCount === 1
                ? aiSummaryFixture({ id: 'sum-1', draft_content: 'Draft one' })
                : aiSummaryFixture({
                    id: 'sum-2',
                    activity_id: 'act-2',
                    activity_slug: 'beacon-app',
                    activity_title: 'Beacon App',
                    member_id: 'member-2',
                    member_readable_id: 'THL-M-2026-0002',
                    member_name: 'Grace Hopper',
                    draft_content: 'Draft two',
                  }),
          }
        },
        '/api/admin/ai/summaries/sum-1': {
          body: aiSummaryFixture({ id: 'sum-1', draft_content: 'Draft one' }),
        },
        // The follow-up refresh fails — the generated summary must still win.
        '/api/admin/ai/summaries/sum-2': {
          status: 500,
          body: { error: { code: 'SERVER_ERROR', message: 'boom' } },
        },
      },
    })

    await selectProject('act-1')
    await waitFor(() => expect(memberSelect().value).toBe('member-1'))
    fireEvent.click(screen.getByRole('button', { name: /generate summary/i }))
    await waitFor(() => expect(within(summaryCard()).getByText('Atlas Engine')).toBeInTheDocument())

    await selectProject('act-2')
    await waitFor(() => expect(memberSelect().value).toBe('member-2'))
    fireEvent.click(screen.getByRole('button', { name: /generate summary/i }))

    await waitFor(() => expect(within(summaryCard()).getByText('Beacon App')).toBeInTheDocument())
    expect(within(summaryCard()).queryByText('Atlas Engine')).not.toBeInTheDocument()
  })

  it('keeps Publish disabled until the draft is saved and reviewed', async () => {
    const reviewed = { value: false }
    renderApp({
      entry: ENTRY,
      handlers: {
        ...adminDataHandlers(),
        '/api/admin/ai/sources': { body: aiSourceOverviewFixture },
        '/api/admin/ai/summaries/generate': {
          body: aiSummaryFixture({ id: 'sum-1', draft_reviewed: false }),
        },
        '/api/admin/ai/summaries/sum-1': (_url: string, init?: RequestInit) => {
          if (init?.method === 'PATCH') {
            reviewed.value = true
            return {
              body: aiSummaryFixture({
                id: 'sum-1',
                draft_content: 'Edited and reviewed.',
                draft_reviewed: true,
              }),
            }
          }
          return { body: aiSummaryFixture({ id: 'sum-1', draft_reviewed: reviewed.value }) }
        },
      },
    })

    await selectProject('act-1')
    await waitFor(() => expect(memberSelect().value).toBe('member-1'))
    fireEvent.click(screen.getByRole('button', { name: /generate summary/i }))

    const publishButton = await screen.findByRole('button', { name: /^publish$/i })
    expect(publishButton).toBeDisabled()

    fireEvent.click(screen.getByRole('button', { name: /save draft/i }))
    await waitFor(() => expect(screen.getByRole('button', { name: /^publish$/i })).toBeEnabled())
  })
})
