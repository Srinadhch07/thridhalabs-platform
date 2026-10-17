# Activities: Projects, Programmes & Hackathons

This document describes **Activities**: a single admin-managed system for the
three kinds of offering the lab runs.

- **Project** — invitation-only. An admin selects members, assigns a role and
  sends email invitations; members reply and the admin confirms them manually.
- **Programme** — open. Eligible members self-register from the member portal.
- **Hackathon** — open. Same self-registration flow as a Programme.

- Backend: FastAPI + MongoDB (`backend/app/modules/activities/`)
- Frontend: React 19 + TypeScript + Vite (`web/src/features/activities/`)
- Storage: existing media library for banners; existing storage provider for
  PDF briefs (never stored in MongoDB).

---

## 1. Overview

An activity carries a title, slug, summary, description, optional dates, an
optional promotional banner, an optional PDF brief, roles offered, tags and a
homepage-featured flag. Its type decides the participation workflow:

| Type      | Entry            | Participation flow                                             |
| --------- | ---------------- | ------------------------------------------------------------- |
| Project   | Invitation only  | invited > interested/declined > confirmed / withdrawn         |
| Programme | Self-register    | self-registered > confirmed / withdrawn                       |
| Hackathon | Self-register    | self-registered > confirmed / withdrawn                       |

Sending an invitation **never** auto-adds a member as an active participant: it
creates an `invited` participation record. Only `confirmed` members count as the
active roster.

### Status lifecycle

Stored status (`ActivityStatus`): `draft | published | cancelled | archived`.

- **Draft** — never public, never promotable.
- **Published** — public; open types accept registration; projects accept
  invitations.
- **Cancelled** — kept reachable by slug but clearly marked, never promoted.
- **Archived** — hidden everywhere; participation history preserved.

A separate, **derived** presentation label (`ActivityPresentationStatus`:
`upcoming | ongoing | completed | cancelled | archived`) is computed from the
stored status plus the dates, so the UI can show *Coming soon / Ongoing /
Completed* without the admin maintaining it. The stored status is the source of
truth.

---

## 2. Data model

### `activities`
`id, title, slug (unique), activity_type, summary, description, status,
start_date, end_date, banner_media_id, featured, display_order, roles_offered,
tags, brief (current pointer), brief_history, cancel_reason, timestamps`.

Helper methods on `Activity`:
`is_open_registration()`, `registration_open(today)`,
`presentation_status(today)`.

### `activity_participations`
`id, activity_id, member_id, role, status, source, note, invited_at,
responded_at, confirmed_at, withdrawn_at, email_sent_at, timestamps`.

A **unique `(activity_id, member_id)` index** makes duplicate participation
impossible. Deleting an activity (hard delete) cascades to delete its
participation records.

Indexes are created in `backend/app/db/indexes.py` (slug uniqueness; status /
type / featured / display-order queries; the participation unique + lookup
indexes).

---

## 3. API

### Admin — `/admin/activities` (editor+; delete admin+; CSRF on mutations)
- `GET /` — paginated list (filter by status / type / featured).
- `POST /` — create.
- `GET /{id}` — detail.
- `PATCH /{id}` — update (lifecycle, dates, banner, featured, order, roles…).
- `DELETE /{id}` — hard delete (admin+), cascades participations.
- `POST /{id}/brief` — upload / replace PDF brief (versioned).
- `GET /{id}/brief` — download current brief.
- `DELETE /{id}/brief` — remove current pointer (history retained).
- `POST /{id}/invitations` — invite members to a **published project**.
- `GET /{id}/participants` — paginated roster.
- `PATCH /{id}/participants/{participation_id}` — update status / role / note.

### Public — `/public/activities`
- `GET /` — published activities only (featured filter supported).
- `GET /{slug}` — published **or** cancelled (clearly marked); drafts and
  archived are never returned.
- `GET /{slug}/brief` — download the brief of a public activity.

### Member — `/member/activities` (authenticated member; CSRF on mutations)
- `GET /` — activities plus the member's own participation state.
- `POST /{slug}/register` — self-register (open types only).
- `POST /{slug}/withdraw` — withdraw.

Published activities are also added to the sitemap
(`backend/app/api/routes/seo.py`).

---

## 4. PDF briefs

- Validated by **magic bytes** (`%PDF-`) over the first 1024 bytes; non-PDF
  uploads are rejected (`415`).
- Size limited by `ACTIVITY_BRIEF_MAX_BYTES` (default 20 MiB) → `413`.
- Stored through the configured storage provider; the object key is never
  exposed publicly.
- **Append-only versioning**: replacing a brief bumps the version and keeps
  history; removing clears only the current pointer.
- Drafts/private activities never serve their brief.

---

## 5. Frontend

- Types: `web/src/types/activity.ts` (exported via `types/index.ts`).
- Feature: `web/src/features/activities/{api,hooks,labels}.ts`.
- Public: `pages/public/ActivitiesPage.tsx`,
  `pages/public/ActivityDetailPage.tsx`; homepage carousel
  `components/public/ActivityCarousel.tsx` + `components/public/ActivityCard.tsx`
  (renders only published, featured activities).
- Admin: `pages/admin/AdminActivitiesPage.tsx`,
  `pages/admin/AdminActivityEditPage.tsx`, plus
  `components/admin/ActivityInvitationsPanel.tsx` and
  `components/admin/ActivityParticipantsPanel.tsx`.
- Member: `pages/member/MemberActivitiesPage.tsx`.
- Styles: `web/src/styles/activities.css` (imported in `main.tsx`).
- Routes/nav: `app/router/AppRouter.tsx`, `AdminNav`, `MemberNav`, `Navigation`.

---

## 6. Tests

- Backend: `backend/tests/test_activities.py` (RBAC/CSRF, lifecycle, slug
  uniqueness, date validation, brief validation & versioning, invitations with
  email capture, self-registration/withdrawal, registration windows).
- Frontend: `web/src/test/activities.test.tsx` (public index/detail, homepage
  carousel, admin list/editor/brief/participants/invitations, member register).

---

## 7. Explicitly out of scope

Daily reports, report approval, AI/Groq summarization, certificate issuance,
hackathon submission/judging/scoring/ranking, automated email-reply detection
(IMAP/Gmail/parser), Discord, GitHub, automated member matching, and
recruitment/employment features are **not** part of Activities.
