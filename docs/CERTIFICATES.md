# Certificates — Issuance, Delivery & Public Verification

This document describes the **certificate lifecycle** that follows a successful
[Work Showcase certification review](WORK_SHOWCASE.md): an admin/owner issues a
certificate for one approved work, a PDF (with a QR code) is generated and
stored, the member can download it, an admin can email it, and it can be revoked
with a mandatory reason. Anyone can then **verify** a certificate by its public
ID — including via the QR code's URL.

- Backend: FastAPI + MongoDB (`backend/`)
- Frontend: React 19 + TypeScript + Vite (`web/`)

A certificate recognises **one reviewed work**. It is deliberately scoped: it
must not imply a government, academic, or professional-accreditation credential,
and the PDF/public pages say so explicitly.

---

## 1. Overview

- **Issuance is an explicit action** — issuing is separate from viewing or
  reviewing. It is restricted to `admin`/`owner` roles.
- **One certificate per review request, forever.** A unique index on
  `request_id` backs an idempotent check, so a double-click or a concurrent race
  yields the same certificate rather than a duplicate.
- **Human-readable, collision-resistant IDs.** `THL-CERT-<year>-<12 chars>` from
  a Crockford-style alphabet (no ambiguous `I/O/0/1`), unique-indexed, never
  derived from the sequential Mongo `_id`, and never reused (even after
  revocation).
- **PDF bytes live in object storage**, never in Mongo (only the storage key,
  size, and SHA-256 are stored).
- **The QR code encodes the full verification URL**, built from a configured,
  non-localhost origin. A missing/invalid origin is a hard failure — issuance
  never prints a useless QR.
- **Revocation is a status change with an audit trail** — never a delete, never
  an ID reuse. Revoked certificates remain downloadable and verifiably revoked.
- **Email failure never invalidates a certificate.** Delivery state is tracked
  (`not_sent|sent|failed`) with attempt count and last error; the certificate
  stays valid and downloadable.
- **Public verification leaks nothing private.** Unknown/guessed IDs return `404`;
  the public projection omits email, storage keys, reviewer identity, and any
  private work content (the work link and work presentation are omitted unless
  both the member and the work are currently public).
- **The work shown is the certified version, not the latest edit.** The public
  page presents the approved certification *snapshot* — the exact version that
  was reviewed — so later edits cannot rewrite what was certified. When a
  publicly viewable current version exists it is offered as a separately labelled
  link; a freshness flag marks whether the work changed since certification.

---

## 2. Data model

### `certificates`

| Field                | Type | Notes |
|----------------------|------|-------|
| `id`                 | ObjectId → str internally | **never** exposed as Mongo `_id` |
| `certificate_id`     | str | public ID `THL-CERT-YYYY-XXXXXXXXXXXX`, unique |
| `request_id`         | ObjectId | originating review request; **unique** |
| `work_id`            | ObjectId | |
| `member_id`          | ObjectId | owner (internal) |
| `member_readable_id` | str | e.g. `THL-M-2026-0001` (used to build the public work link) |
| `member_name`        | str | display name captured at issuance |
| `work_title`         | str | snapshot title |
| `work_slug`          | str | snapshot slug |
| `schema_version`     | str | `"1"` (template version) |
| `decided_at`         | datetime \| null | review decision time |
| `issued_at`          | datetime | |
| `issued_by`          | ObjectId → str | issuing admin |
| `issued_by_role`     | str | admin/owner |
| `pdf_object_key`     | str | storage key (never exposed) |
| `pdf_filename`       | str | `Thridha-Labs-Certificate-<id>.pdf` |
| `pdf_size_bytes`     | int | |
| `pdf_sha256`         | str | content hash |
| `qr_verify_url`      | str | full verification URL encoded in the QR |
| `status`             | `issued\|revoked` | |
| `revoked_at`         | datetime \| null | |
| `revoked_by`         | ObjectId → str \| null | |
| `revocation_reason`  | str \| null | ≤ 1000, mandatory on revoke |
| `email_status`       | `not_sent\|sent\|failed` | |
| `email_sent_at`      | datetime \| null | |
| `email_attempts`     | int | |
| `email_last_error`   | str \| null | ≤ 500 |
| `created_at/updated_at` | datetime | |

Indexes: **unique** `certificate_id`; **unique** `request_id`; `issued_at`
(desc); `{member_id, issued_at}`; `status`.

### Configuration

| Setting | Fallback | Purpose |
|---------|----------|---------|
| `CERTIFICATE_VERIFY_BASE_URL` | `FRONTEND_URL` | canonical public origin for verification links / QR |

`Settings.verification_base_url` strips whitespace and trailing slashes and is
validated as an absolute `http(s)` URL when present. At issuance the service
additionally rejects missing, non-http(s), `localhost`/`127.0.0.1`/`0.0.0.0`/
`::1`/`*.local` values with `503 CERTIFICATE_URL_NOT_CONFIGURED`.

---

## 3. Certificate ID, QR & verification URL

- `generate_certificate_id(year)` → `THL-CERT-<year>-<12 random chars>` using
  `ABCDEFGHJKLMNPQRSTUVWXYZ23456789` (32 symbols ⇒ ~10¹⁸ space for 12 chars).
- `build_verification_url(base, id)` → `"{base}/verify-certificate/{id}"`.
- `generate_qr_png(url)` → PNG bytes (`qrcode`, error-correction M).
- The QR is embedded in the PDF; scanning it opens the public verification page.

---

## 4. PDF generation

`app/modules/certificates/pdf.py` (pure/synchronous, `reportlab`):

- A4 **landscape**, brand colours (primary/secondary/text/background) resolved
  best-effort from the branding record; an optional logo is embedded when
  available (failures are logged, never fatal).
- Shows the member name, certified work title (wrapped), issue date, the
  certificate ID, the verification URL, and the QR code.
- `_resolve_fonts` best-effort loads a TTF and falls back to Helvetica.
- `sha256_hex(bytes)` is stored for integrity.

---

## 5. API reference

All paths are prefixed with `/api`. Mutations require the double-submit CSRF
header (`X-CSRF-Token` matching the `thridha_labs_csrf` cookie). Issuance,
revocation and email require `require_role("admin")` (admins + owners; editors
are rejected). Listing/reading/downloading require any active admin/owner.

### Member — certificates (`/member/certificates`)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/member/certificates` | paginated; `status` filter; own certificates only |
| GET | `/member/certificates/{certificate_id}` | 404 unless owned |
| GET | `/member/certificates/{certificate_id}/download` | PDF (`Content-Disposition`) |

### Admin — certificates (`/admin/certificates`)

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| POST | `/admin/certificates` | **admin/owner** | `{request_id}` → approve-if-needed + issue → `201` |
| GET | `/admin/certificates` | any admin | paginated; `status`, `member_id`, `request_id` filters |
| GET | `/admin/certificates/{certificate_id}` | any admin | full admin view (audit fields) |
| GET | `/admin/certificates/{certificate_id}/download` | any admin | PDF |
| POST | `/admin/certificates/{certificate_id}/email` | **admin/owner** | email PDF to the member |
| POST | `/admin/certificates/{certificate_id}/revoke` | **admin/owner** | `{reason}` required |

### Public (`/public`)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/public/certificates/{certificate_id}` | public projection; `404` if unknown |

The certification detail response (`GET /member/certifications/{id}` and the
admin equivalent) now includes a `certificate` reference
(`certificate_id`, `status`, `issued_at`, `email_status`, `work_title`,
`revoked_at`) or `null`.

---

## 6. Lifecycle & workflows

### Issuance (`POST /admin/certificates`)

1. Load the review request (`404 CERTIFICATION_NOT_FOUND` if missing).
2. If a certificate already exists for the request → return it (idempotent).
3. If the request is `submitted`/`under_review` → approve it first (via the
   certifications service, preserving the review audit trail); tolerate a
   concurrent `CERTIFICATION_ALREADY_DECIDED` race and only continue if the
   resulting state is `approved`. Otherwise a non-issuable state returns
   `409 CERTIFICATION_NOT_APPROVED`.
4. Resolve the member display name, generate the ID + verification URL + QR,
   render the PDF, and **store the PDF first**.
5. Insert the certificate record. A `DuplicateKeyError` cleans up the orphan
   object and returns the winning row (race-safe).
6. Nothing is reported as issued until the record exists.

### Revocation (`POST /admin/certificates/{id}/revoke`)

Status flips to `revoked` with `revoked_at/revoked_by/revocation_reason`.
Already-revoked → `409 CERTIFICATE_ALREADY_REVOKED`. The PDF is retained and the
certificate remains downloadable and publicly verifiable as revoked.

### Email (`POST /admin/certificates/{id}/email`)

Reads the member's server-side email (never a client-supplied address), attaches
the PDF, and records `email_status`, `email_attempts`, `email_last_error`.
Delivery failure returns `502 CERTIFICATE_EMAIL_FAILED` and leaves the
certificate valid and downloadable. A missing member → `409
CERTIFICATE_MEMBER_MISSING`.

### Public verification (`GET /public/certificates/{id}`)

Returns `{certificate_id, status, issued_at, member_name, work_title, work_url,
revoked_at, revocation_reason, work}`. `work_url` and the nested `work`
presentation are included only when the member and work are currently public;
otherwise both are omitted (existence is never leaked). Unknown IDs → `404
CERTIFICATE_NOT_FOUND`.

`work` is the **certified presentation** — `{title, summary, cover_media_id,
tags, external_links, content, author, member_profile_url, certified_at,
current_work_url, has_newer_version}` — built from the approved
`CertificationRequest.snapshot` (reached through `Certificate.request_id`), never
from the work's current state, so a member's later edits cannot alter what is
shown. It is populated only while the work is still publicly visible (published
+ public + owner active and profile public); the live work is resolved by its
stable `work_id` (surviving slug renames) solely to gate visibility and to
supply `current_work_url`. `has_newer_version` is true when the work's version
differs from the snapshot's; the presentation still shows the certified snapshot.
Media is referenced by id and served through `/public/media/{id}`; missing assets
degrade gracefully. A missing/legacy snapshot leaves `work` null while
verification still succeeds, and revoked certificates still render (with the
revoked status prominent) without implying validity.

### Error codes (selected)

`CERTIFICATION_NOT_FOUND`, `CERTIFICATION_NOT_APPROVED`,
`CERTIFICATE_NOT_FOUND`, `CERTIFICATE_EXISTS`, `CERTIFICATE_ALREADY_REVOKED`,
`CERTIFICATE_MEMBER_MISSING`, `CERTIFICATE_EMAIL_FAILED`,
`CERTIFICATE_PDF_NOT_FOUND`, `CERTIFICATE_URL_NOT_CONFIGURED`,
`STORAGE_ERROR`, `INVALID_STATUS`.

---

## 7. Security & privacy guarantees

- Certificate PDFs are stored in object storage; Mongo holds only the key/size/
  hash. The object key is never returned by any API.
- All certificate responses omit Mongo `_id`, internal `member_id`, and email.
- Member endpoints are owner-scoped; admin endpoints are role-gated; issuance/
  revoke/email require admin/owner.
- The public projection never exposes private work content, PII, storage keys, or
  reviewer identity; guessed IDs cannot enumerate data.
- Rate limiting on the public verify endpoint is **not** implemented (the app's
  rate limiter is in-memory and login-only) — a documented limitation.

---

## 8. Frontend architecture

### Types
- `web/src/types/certificate.ts` — statuses, member/admin/public projections,
  payloads and query.
- `web/src/types/certification.ts` — `CertificationDetail.certificate:
  CertificateRef | null`.

### Features (api/hooks/status)
- `web/src/features/certificates/{api,hooks,status}.ts` — member/admin/public
  calls + polling-free `useAsync` hooks + status/email labels & chips.
- `web/src/lib/api/client.ts` — new `downloadFile()` helper (credentials-included
  binary GET, never sends CSRF).
- `web/src/lib/utils/download.ts` — `saveBlob()` browser download trigger.

### Components
- `components/certificates/CertificateStatusChip.tsx`
- `components/certificates/CertificateSummary.tsx` — identity, verify link, PDF
  download (scope-aware).
- `components/certificates/CertificateRefSection.tsx` — loads a referenced
  certificate for the member/admin detail panel.
- `components/certificates/CertificatePanel.tsx` — admin issue / email / revoke
  controls.
- `components/certificates/CertifiedWorkSection.tsx` — the certified work
  presentation on the public verification page (reuses `ContentRenderer`,
  `TechChips`, `MediaTile`, `MemberAvatar`).
- `components/certifications/CertificationDetailPanel.tsx` — optional
  `certificateScope` renders the member certificate summary.

### Pages & routes

| Path | Page |
|------|------|
| `/verify-certificate/:certificateId` | `VerifyCertificatePage` (public) |
| `/admin/certificates` | `AdminCertificatesPage` |
| `/admin/certifications/:requestId` | `AdminCertificationDetailPage` (+ certificate panel) |
| `/member/certifications` | `MemberCertificationsPage` (+ certificate summary) |

`AdminNav` gains a **Certificates** link.

### Styles
Certificate styles appended to `web/src/styles/works.css` (token-driven,
imported in `main.tsx`). Class prefixes: `.certificate-*`, `.verify-*`,
`.cert-work*`.

---

## 9. Testing & verification

- Backend: `backend/tests/test_certificates.py` (+28) — RBAC/CSRF, auto-approve,
  already-approved, rejected→409, idempotent + concurrent single-issue,
  unique/well-formed IDs, filters, member isolation, PDF validity, **QR decoded
  from the generated PDF** (via `pypdf` image extraction + `opencv`), public
  verify (issued/revoked/unknown/private-work), URL-unconfigured & localhost
  `503`, storage-failure `500`, revoke reason/CSRF/RBAC, revoke idempotency +
  still-downloadable, no reissue after revoke, email success + failure. The
  certified-work tests assert the snapshot is unchanged after a member edit,
  `has_newer_version` flips, the current-version link follows a slug rename, and
  the section is omitted for private/unpublished/missing-snapshot work.
- Frontend: `web/src/test/certificates.test.tsx` (+9) — member summary +
  download, public verify (issued/revoked/unknown), admin list, issue from
  review, email + revoke, editor lockout, admin nav. Certified-work tests cover
  the full presentation, the "updated since certified" label, omission when no
  public work exists, and rendering on a revoked certificate.

| Check | Command | Result |
|-------|---------|--------|
| Backend certificate suite | `python -m pytest tests/test_certificates.py -q` | 28 passed |
| Frontend tests | `npx vitest run --no-file-parallelism` | **217 passed** (22 files) |
| Type-check | `npx tsc --noEmit` | clean |
| Production build | `npx vite build` | success |

Baseline before this feature: 208 frontend tests. (Under heavy parallel load on
a slow machine the jsdom suite is flaky; it is green with `--no-file-parallelism`.)

---

## 10. Final report — 24-item checklist

### Backend
1. **Certificate model** — `certificates` collection, ID/QR/audit/email fields,
   `schema_version`, status/email enums. ✅
2. **Certificate ID generator** — Crockford-style, human-readable, unique-indexed,
   never sequential-derived. ✅
3. **PDF renderer** — brand-aware A4 landscape certificate with QR + ID + URL. ✅
4. **Repository** — insert/find-by-id/find-by-public-id/find-by-request/
   update/list over `certificates`. ✅
5. **Verification URL config** — `CERTIFICATE_VERIFY_BASE_URL` (+ `FRONTEND_URL`
   fallback), property, validation. ✅
6. **Issuance service** — explicit action, approve-if-needed, idempotent,
   race-safe, store PDF before record. ✅
7. **Revocation service** — status change + reason + audit, no reuse/delete. ✅
8. **Email delivery** — PDF attachment, attempts/errors tracked, non-fatal. ✅
9. **Member/admin reads + download** — owner-scoped member, role-gated admin. ✅
10. **Public verification** — privacy-safe projection, uniform 404, guarded work
    link. ✅
11. **Routers** — `admin_router.py`, `router.py`, `public.py`, CSRF, RBAC,
    `_ERROR_RESPONSES`. ✅
12. **Indexes + wiring** — unique `certificate_id`/`request_id`, list indexes,
    routers registered in `main.py`; certification detail exposes `certificate`. ✅
13. **Email attachment support** — `EmailAttachment` + `send_email(attachments=)`
    in the shared email service. ✅

### Frontend
14. **Types** — certificate projections/payloads + certification `certificate`
    ref. ✅
15. **Feature modules** — certificates api/hooks/status. ✅
16. **Binary download helper** — `downloadFile()` + `saveBlob()`. ✅
17. **Member UI** — certificate summary + PDF download in the member detail. ✅
18. **Admin controls** — issue / email / revoke panel on the review detail. ✅
19. **Admin list** — `/admin/certificates` queue with download + request link. ✅
20. **Public verification page** — issued / revoked / not-found states. ✅

### Verification
21. **Routing & nav** — public `/verify-certificate/:id`, admin route, nav link. ✅
22. **Styles** — token-driven certificate/verification CSS. ✅
23. **Backend tests** — 28 certificate tests pass (QR decoded from the PDF). ✅
24. **Frontend tests + build** — 217 tests pass, `tsc` clean, `vite build`
    succeeds. ✅

All 24 items complete. No secrets were read or modified; the root `.env` was
untouched; no real accounts were created and no deployment was performed.

---

## 11. Certified work presentation (public verification)

The public verification page (`/verify-certificate/:certificateId`) can present
the actual work behind a certificate — "The work behind this certificate" —
without weakening any privacy rule.

- **Source of truth = the certified snapshot.** The presentation is built from
  the approved `CertificationRequest.snapshot`, reached via
  `Certificate.request_id`. It is the immutable version the reviewer ruled on, so
  edits made after certification never change what is displayed (the certificate's
  frozen `work_title` is likewise untouched).
- **Current eligibility gates exposure.** The work is shown only while it is
  published, public-visible, and its owner is active with a public profile — the
  same derived predicate the public work pages use. The live work is resolved by
  its stable `work_id` (not the frozen slug), so the link keeps working after a
  rename. If any gate fails, `work` and `work_url` are both omitted (nothing is
  leaked).
- **Certified vs. current.** When a publicly viewable current version exists,
  `current_work_url` points at it and is labelled distinctly ("View the current
  version"). `has_newer_version` marks whether the work changed since the
  snapshot; the presentation itself still renders the certified snapshot.
- **Robust edge cases.** A missing/legacy snapshot yields `work: null` while
  verification still succeeds. Revoked certificates still render the work, with
  the revoked status shown prominently and no implication of validity. Media is
  referenced by id and served through the public media route; a missing asset
  degrades to the placeholder rather than breaking the page.
- **Key files.** `backend/app/modules/certificates/schemas.py`
  (`PublicCertificateWork`), `backend/app/modules/certificates/service.py`
  (`_public_work_presentation` + `get_public`),
  `backend/app/modules/works/service.py` (`get_public_work_by_id`),
  `web/src/types/certificate.ts`, `web/src/components/certificates/CertifiedWorkSection.tsx`,
  `web/src/pages/public/VerifyCertificatePage.tsx`.
