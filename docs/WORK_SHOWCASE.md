# Work Showcase & Certification Review

This document describes the **Work Showcase** system (member-authored,
block-structured works with public profiles) and the **Certification Review**
workflow (members submit published works; admins/owners review a frozen snapshot
and record a decision). Certificate *generation/delivery* is intentionally out
of scope.

- Backend: FastAPI + MongoDB (`backend/`)
- Frontend: React 19 + TypeScript + Vite (`web/`)

---

## 1. Overview

A member owns a set of **works**. Each work has metadata (title, summary, tags,
cover image, external links) plus a strict, versioned **content document** built
from typed blocks (never raw HTML). Works have independent **visibility**
(`private|members|public`) and **publication status**
(`draft|published|unpublished`), and can be submitted for a **certification
review**.

Public exposure requires **all** of: the author's account is `active`, the
author's profile visibility is `public`, the work is `published`, and the work's
visibility is `public`. Otherwise the public endpoints return `404` (existence is
never leaked).

---

## 2. Data model

### `member_works`

| Field                | Type                          | Notes |
|----------------------|-------------------------------|-------|
| `id`                 | ObjectId (serialized as str)  | never exposed as Mongo `_id` |
| `member_id`          | ObjectId                      | owner |
| `title`              | str ≤ 150                     | |
| `slug`               | str                           | `slugify(title)`, unique per member |
| `summary`            | str ≤ 2000                    | required |
| `cover_media_id`     | ObjectId \| null              | owned media |
| `tags`               | str[] ≤ 50 (each ≤ 100)       | |
| `external_links`     | `{label,url}[]` ≤ 20          | http(s) only |
| `content`            | ContentDocument (`version:1`) | see §3 |
| `visibility`         | `private\|members\|public`    | default `private` |
| `publication_status` | `draft\|published\|unpublished` | default `draft` |
| `version`            | int                           | `$inc` on every update/publish/unpublish |
| `created_at/updated_at/published_at` | datetime | |

Indexes: unique `{member_id, slug}`; listing indexes for
`{member_id, created_at}`, `{member_id, updated_at}`, `{member_id, status}`.

### `certification_requests`

| Field                | Type | Notes |
|----------------------|------|-------|
| `id`                 | ObjectId → str | |
| `work_id`            | ObjectId | |
| `member_id`          | ObjectId | |
| `status`             | `submitted\|under_review\|changes_requested\|approved\|rejected` | |
| `active`             | bool | `True` for non-terminal + `changes_requested` |
| `snapshot`          | frozen copy: slug/title/summary/cover/tags/external_links/content | captured at submission |
| `snapshot_version`   | int | work `version` captured |
| `version_reviewed`   | int | work `version` the review judged |
| `decisions`          | `{action,by,by_role,at,feedback}[]` | append-only audit trail |
| `latest_feedback`    | str \| null | |
| `submitted_at/decided_at/captured_at/created_at/updated_at` | datetime | |

Index: partial unique `{work_id}` where `active:true` → one active request per
work. `changed_since_review = status ∈ {approved,rejected} and work.version >
version_reviewed`.

### `member_profiles.profile_visibility`

Added `ProfileVisibility` (`private|members|public`, default `private`).
`MemberProfileUpdate.profile_visibility = ProfileVisibility | None` where
`None` means "keep current".

---

## 3. Content document schema

Strict JSON, `version: 1`, `blocks: ContentBlock[]` (≤ 100). Discriminated union
on `type`:

| Block            | Shape | Limits |
|------------------|-------|--------|
| `paragraph`      | `spans: InlineRun[]` | total text ≤ 100_000 |
| `heading`        | `level: 2\|3\|4`, `text` | |
| `image`          | `media_id`, `caption?`, `alt?` | alt ≤ 300, caption ≤ 300 |
| `image_gallery`  | `media_ids: string[]` | ≤ 20 |
| `bulleted_list`  | `items: string[]` | ≤ 100 items, each ≤ 5000 |
| `numbered_list`  | `items: string[]` | ≤ 100 items, each ≤ 5000 |
| `quote`          | `text`, `attribution?` | ≤ 8000 |
| `code`           | `code`, `language` | code ≤ 20000 |
| `external_link`  | `label`, `url` | label ≤ 200, url ≤ 2000, http(s) only, both required |
| `divider`        | — | |

`InlineRun = {text, bold?, italic?, code?, link?}`. All models use
`extra="forbid"`. Templates (client-side seeds): `blank-canvas`,
`project-showcase`, `research`, `creative-portfolio`.

---

## 4. API reference

All paths are prefixed with `/api`. Mutations require the double-submit CSRF
header (`X-CSRF-Token` matching the `thridha_labs_csrf` cookie).

### Member — works (`/member/works`)

| Method | Path | Body / notes |
|--------|------|--------------|
| POST   | `/member/works` | create (starts private draft) → `201` |
| GET    | `/member/works` | paginated; `page`,`page_size`,`status`,`sort` (`newest\|oldest\|title\|updated`) |
| GET    | `/member/works/{work_id}` | full work (with content) |
| PATCH  | `/member/works/{work_id}` | patch-style update; **never publishes** |
| DELETE | `/member/works/{work_id}` | `409 CERTIFICATION_IN_PROGRESS` while active |
| POST   | `/member/works/{work_id}/publish` | explicit publish |
| POST   | `/member/works/{work_id}/unpublish` | explicit unpublish |

### Member — media (`/member`)

| Method | Path | Notes |
|--------|------|-------|
| GET    | `/member/media` | paginated list of the member's uploads |
| POST   | `/member/media` | upload image (owned by member); foreign dedup → `409 MEDIA_NOT_OWNED` |

### Member — certifications (`/member/certifications`)

| Method | Path | Notes |
|--------|------|-------|
| POST   | `/member/certifications` | apply/resubmit (`{work_id}`); published + owned required |
| GET    | `/member/certifications` | paginated; `status` filter |
| GET    | `/member/certifications/{request_id}` | detail (+ snapshot/history) |

### Admin — certifications (`/admin/certifications`)

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET    | `/admin/certifications` | any admin (editor+) | paginated; `status` filter |
| GET    | `/admin/certifications/{request_id}` | any admin (editor+) | frozen snapshot |
| POST   | `/admin/certifications/{request_id}/decision` | **admin/owner only** | `{action, feedback?}` |

`action ∈ {under_review, approve, request_changes, reject}`. `feedback` is
mandatory for `request_changes` and `reject`.

### Public (`/public`)

| Method | Path | Notes |
|--------|------|-------|
| GET    | `/public/members/{member_id}` | public member profile + published works |
| GET    | `/public/members/{member_id}/works/{slug}` | single published public work |
| GET    | `/public/media/{media_id}?variant=original\|thumb\|md\|lg` | public media delivery |

Public member/work lookups `404` uniformly when the eligibility rules (§1) are
not met. Public responses never include Mongo `_id`.

---

## 5. Certification workflow

1. Member **publishes** a work (eligibility gate: published + owned).
2. Member **applies** → a request is created with a **frozen snapshot** and
   `status = submitted`, `active = true`.
3. Reviewer (admin/owner) may move it to `under_review`, or decide directly:
   - `approve` → terminal, `active = false`
   - `reject` → terminal, `active = false`, feedback mandatory
   - `request_changes` → `active = true`, feedback mandatory; the member edits
     and **resubmits** (same request, new snapshot) → `submitted`
4. Reviewers only ever see the snapshot. If the live work changes after a
   terminal decision, `changed_since_review` becomes `true`.

`WorkCertificationRef.reviewable` is `true` when the work is published and has
no request or the request is in a decided/changes state — i.e. it is safe to
submit again.

### Error codes (selected)

`WORK_NOT_FOUND`, `WORK_NOT_PUBLISHED`, `CERTIFICATION_NOT_FOUND`,
`CERTIFICATION_ALREADY_ACTIVE`, `CERTIFICATION_ALREADY_DECIDED`,
`CERTIFICATION_AWAITING_RESUBMIT`, `CERTIFICATION_IN_PROGRESS`,
`FEEDBACK_REQUIRED`, `CONTENT_TOO_LARGE`, `INVALID_STATUS`, `MEDIA_NOT_OWNED`.

---

## 6. Frontend architecture

### Types
- `web/src/types/work.ts` — content blocks, `MemberWork`, `WorkCard`, public
  work types, payloads/queries.
- `web/src/types/certification.ts` — statuses, snapshot, decisions, detail/list.
- `web/src/types/member.ts` — `ProfileVisibility`, `PublicMemberProfile`.

### Features (api/hooks/status)
- `web/src/features/works/{api,hooks,status}.ts`
- `web/src/features/certifications/{api,hooks,status}.ts`
- member media: `web/src/features/media/{api,hooks}.ts`
- `web/src/features/members/{api,hooks}.ts` (`getPublicMember`/`usePublicMember`)

### Components
- `components/works/ContentRenderer.tsx` — read-only block renderer (shared by
  preview + public page + snapshot).
- `components/works/BlockEditor.tsx` — editor for the block schema.
- `components/form/ImageUploadField.tsx` — shared contextual `ImageUploadField`
  (single) + `ImageGalleryField` (ordered gallery) used for the cover image and
  the `image` / `image_gallery` blocks. Member works upload via
  `uploadMemberMedia` (`/member/media`) and preview existing references through
  the public media route. See [`IMAGE_UPLOADS.md`](./IMAGE_UPLOADS.md).
- `components/works/templates.ts` — `seedTemplate`.
- `components/works/WorkCard.tsx`.
- `components/certifications/{CertificationStatusChip,CertificationSnapshotView,DecisionHistory,CertificationDetailPanel}.tsx`.

### Pages
- Member: `MemberWorksPage`, `WorkEditorPage`, `WorkPreviewPage`,
  `MemberCertificationsPage`.
- Public: `PublicMemberPage`, `PublicWorkPage`.
- Admin: `AdminCertificationsPage`, `AdminCertificationDetailPage`.

### Routes
| Path | Page |
|------|------|
| `/member/works` | MemberWorksPage |
| `/member/works/new`, `/member/works/:workId/edit` | WorkEditorPage |
| `/member/works/:workId/preview` | WorkPreviewPage |
| `/member/certifications` | MemberCertificationsPage |
| `/members/:memberId` | PublicMemberPage |
| `/members/:memberId/works/:slug` | PublicWorkPage |
| `/admin/certifications` | AdminCertificationsPage |
| `/admin/certifications/:requestId` | AdminCertificationDetailPage |

`MemberNav` gains **Work Showcase** and **Certifications**; `AdminNav` gains
**Certifications**. `MemberProfilePage` gains a **profile visibility** select.

### Styles
New `web/src/styles/works.css` (imported in `main.tsx` after `member.css`),
token-driven so all surfaces follow the branding theme. Work/certification class
prefixes: `.work-*`, `.block-*`, `.image-upload__*`, `.image-gallery__*`,
`.cert-*`, `.public-member__*`, `.public-work*`, `.member-toolbar`.

---

## 7. Testing & verification

- Backend: `backend/tests/test_works.py` (+18) and `test_certifications.py`
  (+13) run against a dedicated `thridha_labs_test` database and isolated
  storage, removed automatically — the real database is never touched.
- Frontend: `web/src/test/{works,certifications,public-members}.test.tsx`
  (23 tests) using the shared `renderApp` / fetch-mock harness.

Verified results:

| Check | Command | Result |
|-------|---------|--------|
| Backend suite | `python -m pytest -q` | **358 passed** (EXIT 0) |
| Type-check | `npx tsc --noEmit` | clean (EXIT 0) |
| Frontend tests | `npx vitest run` | **208 passed** (21 files) |
| Production build | `npx vite build` | success |

Baseline before this feature: 327 backend + 185 frontend tests.

---

## 8. Final report — 24-item checklist

### Backend
1. **Member work model** — `member_works` with metadata, visibility,
   publication status, monotonic `version`. ✅
2. **Content schema** — strict `version:1` block union with per-field limits and
   `extra="forbid"`. ✅
3. **Works repository/service** — create/list/get/update/delete + explicit
   publish/unpublish; `$inc` version. ✅
4. **Works router** — `/member/works` endpoints, CSRF on mutations, owner
   scoping, `_ERROR_RESPONSES`. ✅
5. **Member media API** — `/member/media` list + upload, ownership enforced,
   foreign-dedup `409 MEDIA_NOT_OWNED`. ✅
6. **Profile visibility** — `ProfileVisibility` end-to-end
   (model → schema → serialization → public exposure). ✅
7. **Certification model** — `certification_requests`, snapshot fields,
   append-only decisions, partial-unique active index. ✅
8. **Certification service** — apply/resubmit, list, decide, eligibility, error
   codes, `changed_since_review`. ✅
9. **Certification routers** — member + admin (`admin_router.py`), decisions via
   `require_role("admin")`, reads via `get_active_admin`. ✅
10. **Public APIs** — `GET /public/members/{id}` and
    `/public/members/{id}/works/{slug}` with uniform 404 and no `_id` leakage. ✅
11. **Indexes** — works uniqueness/listing + certification active uniqueness. ✅
12. **Sitemap** — member/work public URLs added to `seo.py`. ✅

### Frontend
13. **Types** — work, certification, and member (`PublicMemberProfile`) types. ✅
14. **Feature modules** — works/certifications api+hooks+status; member media;
    public member/work. ✅
15. **Content rendering** — `ContentRenderer` shared by preview/public/snapshot. ✅
16. **Block editor** — `BlockEditor` + templates + contextual `ImageUploadField`
    / `ImageGalleryField` fields. ✅
17. **Member pages** — works list, editor, preview, certifications. ✅
18. **Public pages** — member profile + public work. ✅
19. **Admin pages** — review queue + decision detail (RBAC-gated, mandatory
    feedback). ✅
20. **Wiring** — routes, `MemberNav`/`AdminNav`, profile visibility select, new
    `works.css`. ✅

### Verification
21. **Backend regression + live verification** — 358 passed against the isolated
    test DB. ✅
22. **Frontend type-check** — `tsc --noEmit` clean. ✅
23. **Frontend tests** — 208 passed (185 baseline + 23 new). ✅
24. **Production build** — `vite build` succeeds. ✅

All 24 items complete. No secrets were read or modified; the root `.env` was
untouched; no real accounts were created and no deployment was performed.
