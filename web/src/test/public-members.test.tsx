/**
 * Public member profiles + public work pages: a member's public profile and
 * their published works, and a single public work by member + slug.
 *
 * The public profile endpoint only ever returns published, public-visible
 * works whose author has an active, public profile — drafts, member-only works,
 * private works and private-profile members never reach this surface.
 */

import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import {
  publicMemberFixture,
  publicMemberMultiWorksFixture,
  publicMemberNoWorksFixture,
  publicWorkFixture,
} from './fixtures'
import { renderApp } from './helpers'

const MEMBER_ID = publicMemberFixture.member_id

describe('public member profile', () => {
  it('shows the member details and their published works', async () => {
    renderApp({
      entry: `/members/${MEMBER_ID}`,
      handlers: {
        [`/api/public/members/${MEMBER_ID}`]: { body: publicMemberFixture },
      },
    })

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Ada Lovelace' }),
    ).toBeInTheDocument()
    expect(screen.getByText(MEMBER_ID)).toBeInTheDocument()
    expect(screen.getByText('Lab member working on embodied AI.')).toBeInTheDocument()

    const work = screen.getByRole('link', { name: /view work: embodied agents/i })
    expect(work).toHaveAttribute('href', `/members/${MEMBER_ID}/works/embodied-agents`)
  })

  it('renders every published work with its tags and work links', async () => {
    renderApp({
      entry: `/members/${MEMBER_ID}`,
      handlers: {
        [`/api/public/members/${MEMBER_ID}`]: { body: publicMemberMultiWorksFixture },
      },
    })

    const first = await screen.findByRole('link', { name: /view work: embodied agents/i })
    expect(first).toHaveAttribute('href', `/members/${MEMBER_ID}/works/embodied-agents`)

    const second = screen.getByRole('link', { name: /view work: neural echoes/i })
    expect(second).toHaveAttribute('href', `/members/${MEMBER_ID}/works/neural-echoes`)

    // Tags are scoped to each work card (Robotics also appears in the skills list).
    expect(within(first).getByText('Robotics')).toBeInTheDocument()
    expect(within(first).getByText('AI')).toBeInTheDocument()
    expect(within(second).getByText('Creative Coding')).toBeInTheDocument()
    expect(within(second).getByText('Audio')).toBeInTheDocument()
  })

  it('shows a friendly empty state when there is no published work', async () => {
    renderApp({
      entry: `/members/${MEMBER_ID}`,
      handlers: {
        [`/api/public/members/${MEMBER_ID}`]: { body: publicMemberNoWorksFixture },
      },
    })

    expect(await screen.findByText(/no public works yet/i)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /view work:/i })).not.toBeInTheDocument()
  })

  it('shows the not-found state for a non-public member', async () => {
    renderApp({
      entry: `/members/${MEMBER_ID}`,
      handlers: {
        [`/api/public/members/${MEMBER_ID}`]: {
          status: 404,
          body: { error: { code: 'MEMBER_NOT_FOUND', message: 'not found' } },
        },
      },
    })

    expect(await screen.findByText(/page not found/i)).toBeInTheDocument()
  })

  it('shows an error state when the profile request fails', async () => {
    renderApp({
      entry: `/members/${MEMBER_ID}`,
      handlers: {
        [`/api/public/members/${MEMBER_ID}`]: {
          status: 500,
          body: { error: { code: 'SERVER_ERROR', message: 'boom' } },
        },
      },
    })

    expect(await screen.findByText(/unable to load member/i)).toBeInTheDocument()
  })
})

describe('public work page', () => {
  it('renders the structured content and external links', async () => {
    renderApp({
      entry: `/members/${MEMBER_ID}/works/embodied-agents`,
      handlers: {
        [`/api/public/members/${MEMBER_ID}/works/embodied-agents`]: { body: publicWorkFixture },
      },
    })

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Embodied Agents' }),
    ).toBeInTheDocument()
    expect(screen.getByText('A study of embodied AI agents.')).toBeInTheDocument()
    expect(screen.getByText('An embodied AI experiment.')).toBeInTheDocument()

    const repo = screen.getAllByRole('link', { name: /repository/i })
    expect(repo.some((link) => link.getAttribute('href') === 'https://github.com/example/embodied')).toBe(
      true,
    )
  })

  it('shows the not-found state for an unpublished work', async () => {
    renderApp({
      entry: `/members/${MEMBER_ID}/works/embodied-agents`,
      handlers: {
        [`/api/public/members/${MEMBER_ID}/works/embodied-agents`]: {
          status: 404,
          body: { error: { code: 'WORK_NOT_FOUND', message: 'not found' } },
        },
      },
    })

    expect(await screen.findByText(/page not found/i)).toBeInTheDocument()
  })
})
