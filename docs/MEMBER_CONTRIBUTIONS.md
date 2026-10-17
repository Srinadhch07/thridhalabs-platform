# Member Contributions to Official Projects

This document describes **Member Contributions**: the workflow that lets Lab
Members submit their existing **Work Showcase** works for **publication review**,
lets Admin/Owner review and publish them, and lets Admin/Owner **feature**
eligible published works on the official **Projects** page — all while reusing
the existing work records (no second editor, no duplicated content).

- Backend: FastAPI + MongoDB (`backend/`)
- Frontend: React 19 + TypeScript + Vite (`web/`)
- Builds on [`WORK_SHOWCASE.md`](./WORK_SHOWCASE.md).

---

## 1. Overview

Two independent decisions are involved:

1. **Publication review** — a member cannot publish a work to the public site on
   their own any more than they can before; they submit it, and an
   admin/owner approves it (or requests changes / rejects it).
2. **Featuring** — being published is *not* the same as being shown on the
   official Projects page. An admin/owner separately curates which eligible
   published works appear there, with a display classification.

Both the legacy direct **publish** endpoint and the new review workflow coexist.
Existing behaviour and tests are preserved.

### Publication status lifecycle

```
draft ──submit──▶ pending_review ──approve──▶ published
  ▲                    │                         │
  │                 withdraw                 unpublish
  │                    │                         ▼
  └────────────────────┴──────────────▶ unpublished / draft
                       │
        request_changes│reject
                       ▼
        changes_requested ──(member edits)──▶ resubmit ──▶ pending_review
             rejected ────(member edits)─────▶ resubmit ──▶ pending_review
```

`WorkPublicationStatus` is now `draft | pending_review | changes_requested |
rejected | published | unpublished`.

### Public exposure

Public exposure of a featured contribution uses the ordinary composite rule
(unchanged): the work is `published`, the work's visibility is `public`, the
author's account is `active`, and the author's profile visibility is `public`.
Featuring **never widens visibility** — the public contributions endpoint
re-checks the rule at serve time, so un-featuring or hiding an author removes the
card immediately.

---

## 2. Data model

`member_works` gains review/featuring fields (existing fields unchanged):

| Field                    | Type                       | Notes |
|--------------------------|----------------------------|-------|
| `submitted_at`           | datetime \| null           | when last submitted for review |
| `review_feedback`        | str \| null                | latest reviewer feedback |
| `reviewed_at`            | datetime \| null           | when the last decision was recorded |
| `reviewed_by`            | ObjectId \| null           | reviewing admin |
| `featured_on_projects`   | bool                       | default `false` |
| `featured_classification`| `ProjectType` \| null      | display type on Projects page |
| `featured_at`            | datetime \| null           | |
| `featured_by`            | ObjectId \| null           | curating admin |

`ProjectType` gains `member-contribution`.

Indexes added: `{publication_status, submitted_at desc}` (review queue) and
`{featured_on_projects, publication_status}` (featured listing).

---

## 3. API reference

All paths are prefixed with `/api`. Mutations require the double-submit CSRF
header (`X-CSRF-Token` matching the `thridha_labs_csrf` / member cookie).

### Member — works

| Method | Path | Notes |
|--------|------|-------|
| POST   | `/member/works/{work_id}/submit` | submit for publication review |
| POST   | `/member/works/{work_id}/withdraw` | withdraw a pending submission back to draft |
| POST   | `/member/works/{work_id}/publish` | **legacy** direct publish (kept) |

`submit` is allowed from `draft`, `changes_requested`, `rejected` or
`unpublished`; an already-pending work returns `409 REVIEW_ALREADY_PENDING` and
an already-published work returns `409 WORK_ALREADY_PUBLISHED`. `withdraw` is
allowed from `pending_review` or `changes_requested`.

### Admin — works (`/admin/works`)

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET    | `/admin/works` | any admin (editor+) | paginated; `status`, `featured`, `sort`, `order` |
| GET    | `/admin/works/{work_id}` | any admin (editor+) | full work incl. content |
| POST   | `/admin/works/{work_id}/decision` | **admin/owner only** | `{action, feedback?}` |
| POST   | `/admin/works/{work_id}/feature` | **admin/owner only** | `{featured, classification?}` |

`action ∈ {approve, request_changes, reject}`. A decision is only accepted while
the work is `pending_review` (`409 WORK_NOT_IN_REVIEW`). `feedback` is mandatory
for `request_changes` and `reject` (`422 FEEDBACK_REQUIRED`); `approve` publishes
the work.

Featuring requires the work to be `published` (`409 WORK_NOT_PUBLISHED`) **and**
publicly-visible (`409 WORK_NOT_PUBLIC`). Un-featuring is always allowed.

### Public — contributions (`/public/contributions`)

| Method | Path | Notes |
|--------|------|-------|
| GET    | `/public/contributions` | featured, publicly-eligible member works as project-style cards with author attribution |

---

## 4. Frontend

- Types: `web/src/types/work.ts` (`WorkReviewAction`, review/feature fields,
  `AdminWorkCard`/`AdminWorkDetail`/`AdminWorkList`/`AdminWorkQuery`,
  `WorkReviewDecisionPayload`, `WorkFeaturePayload`, `FeaturedContribution*`).
- Feature module: `web/src/features/works/{api,hooks,status}.ts` —
  `submitMemberWork`, `withdrawMemberWork`, `listAdminWorks`, `getAdminWork`,
  `decideAdminWork`, `setAdminWorkFeatured`, `getFeaturedContributions`,
  `useAdminWorks`, `useAdminWork`, `useFeaturedContributions`, plus status labels
  and `WORK_REVIEW_ACTION_LABELS`.
- Member: `WorkEditorPage` gains a **Publication review** panel (submit /
  resubmit / withdraw + reviewer feedback).
- Admin: `AdminWorksPage` (review queue with status + featured filters) and
  `AdminWorkDetailPage` (content preview, decision form, featuring form).
- Public: `ContributionCard` renders a featured contribution; `ProjectsPage`
  merges featured contributions into the official grid with author attribution,
  a **Member contributions** filter, and links to
  `/members/{memberId}/works/{slug}`.
- Wiring: routes `works` / `works/:workId` in `AppRouter`, **Publication review**
  in `AdminNav`, and `member-contribution` labels in
  `components/public/labels.ts` / `AdminProjectsPage`.

---

## 5. Testing & verification

- Backend: `backend/tests/test_publication_review.py` (15 tests) — member
  submit/withdraw/resubmit, admin queue/detail/decision/featuring, eligibility
  guards, public contribution listing and privacy re-checking. Shared helpers in
  `_content_helpers.py` (`submit_work`, `withdraw_work`, `review_work`,
  `feature_work`). Regression: existing `test_works`, `test_certifications`,
  `test_certificates`, `test_projects` unchanged.
- Frontend: `web/src/test/publication-review.test.tsx` (10 tests) — member
  editor panel, admin queue + decision + RBAC + featuring, and the public
  Projects-page merge/filter, using the shared `renderApp` / fetch-mock harness.

| Check | Command | Result |
|-------|---------|--------|
| Type-check | `npm run typecheck` | clean |
| Frontend tests | `npm test -- --no-file-parallelism --run` | **267 passed** (25 files) |
| Production build | `npm run build` | success (pre-existing chunk-size warning only) |

No secrets were read or modified; the root `.env` was untouched; no production
records were changed and no deployment was performed.
