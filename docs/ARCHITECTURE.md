# Thridha Labs — Architecture

Status: **Phase 1 — Foundation, Phase 2 — Authentication, Phase 3 —
Storage + Media and Phase 4 — Content APIs implemented.** This document
describes the architecture that exists today and the approved plan for later
phases.

## 1. System overview

```text
Public Website / Admin Panel
            ↓
     React / TypeScript
            ↓
      FastAPI  /api
      ↓            ↓
  MongoDB      Storage
          (local disk or S3)
```

- The **frontend** (React + TypeScript + Vite) renders the public website and
  the admin panel. In development it proxies `/api` to the backend, so the app
  is same-origin.
- The **backend** (FastAPI) exposes a JSON API under the `/api` prefix and is
  the only component that talks to the database or to object storage.
- **MongoDB** stores all application data (including media metadata).
- **Storage** is abstracted behind a provider interface and holds the actual
  media objects (image files) on local disk or in an S3-compatible bucket.

Added incrementally in later phases: the public website (built on the Phase 4
public content endpoints), the admin panel, SMTP delivery and SEO artifacts.

## 2. Backend

Implemented in `backend/`:

- **FastAPI** application assembled in `app/main.py` (`create_app()` factory
  plus a `lifespan` handler).
- **Pydantic settings** (`app/core/config.py`) load the repository-root `.env`
  by absolute path, using the existing environment variable **names** as a
  fixed contract. Secret values are wrapped in `SecretStr` so they cannot be
  printed or serialized accidentally.
- **Configuration validation** fails fast on invalid input: no CORS wildcard,
  well-formed origins, `SameSite=None` requires `Secure`, valid storage mode
  enum, absolute `API_PREFIX`, and (in production) `COOKIE_SECURE=true` plus a
  JWT secret of sufficient length.
- **Motor** (`app/db/mongo.py`) provides async MongoDB access: client
  creation, ping with latency, database accessor and clean shutdown. Only
  exception class names are ever logged — never connection strings.
- **API prefix**: all routes are mounted under `API_PREFIX` (`/api`).
- **Lifespan**: logs a non-sensitive startup summary, connects to MongoDB
  (non-fatal if unreachable — readiness degrades instead), creates required
  indexes when reachable (a failure here is fatal: uniqueness must hold),
  initialises the storage provider (a misconfigured provider, e.g. S3 without
  `AWS_*`, is fatal at startup), and closes the client on shutdown.
- **Logging** (`app/core/logging.py`): structured single-line format driven by
  `LOG_LEVEL`, tightened by `DEBUG`. Passwords, JWT secrets, cookies, cloud
  credentials and `.env` values must never be logged.
- **CORS**: allow-list parsed from `CORS_ORIGINS` with credentials enabled for
  the future cookie-based auth; `*` is rejected at startup.
- **Health endpoints**:
  - `GET /api/health` → `200` liveness (app, version, environment, timestamp)
  - `GET /api/health/ready` → `200` when MongoDB answers a ping, otherwise
    `503` with `status: degraded`

### Authentication (Phase 2)

Layering: `router → service → repository`. Routes only validate/shape input,
services own the flows, repositories own persistence.

- **Accounts** live in the `admins` collection. A unique index on `email`
  (created at startup by `app/db/indexes.py`) enforces uniqueness at the
  database level; emails are normalised (trimmed, lowercased) identically at
  creation and login.
- **Passwords** are hashed with bcrypt (`app/core/security.py`). The policy is
  10–72 characters (bcrypt truncates longer input) and is enforced whenever a
  password is chosen. A dummy bcrypt verification equalises timing for unknown
  emails.
- **Sessions**: an HS256 JWT carrying `sub` (admin id), `role`, `tv` (token
  version), `iat`, `exp`, signed with `JWT_SECRET`, delivered in an HttpOnly
  cookie (`COOKIE_NAME`, max-age from `JWT_ACCESS_MINUTES`). Authentication
  checks signature/expiry, that the admin still exists, and that `tv` matches
  the stored `token_version`.
- **Revocation**: logout bumps `token_version`, invalidating every outstanding
  token for that account immediately, then clears both cookies.
- **CSRF**: double-submit. `GET /api/auth/csrf` issues a readable,
  non-HttpOnly cookie; every state-changing request must echo its value in the
  `X-CSRF-Token` header (constant-time comparison). Login and logout are
  state-changing and therefore covered; GET requests are exempt.
- **Rate limiting**: an in-memory, fixed-window failed-login limiter per
  client IP (`app/services/rate_limit.py`) driven by
  `LOGIN_RATE_LIMIT_MAX` / `LOGIN_RATE_LIMIT_WINDOW_MINUTES`; a limited client
  receives `429` with `Retry-After`. Counters reset on successful login.
  Process-local by design (documented limitation) and swappable for a
  distributed implementation behind the same interface.
- **RBAC**: `require_role(...)` (`app/deps/auth.py`) gates endpoints by
  privilege rank — `owner` (3) > `admin` (2) > `editor` (1); insufficient
  privilege returns `403 INSUFFICIENT_ROLE`.
- **Error handling** (`app/core/errors.py`): every error uses the envelope
  `{"error": {"code": "...", "message": "..."}}` (validation errors add a
  `fields` map). Submitted values — including passwords — are never echoed;
  unknown-email and wrong-password logins return byte-identical responses.
- **Provisioning**: `python -m app.cli.create_admin` (root script
  `npm run admin:create`) creates accounts interactively; the password is read
  with a hidden prompt and never accepted as an argument.

Endpoints:

| Method | Path                 | Notes                                                        |
|--------|----------------------|--------------------------------------------------------------|
| GET    | `/api/auth/csrf`     | Bootstrap: sets the readable CSRF cookie, returns the token  |
| POST   | `/api/auth/login`    | CSRF required, rate limited; sets HttpOnly session cookies   |
| POST   | `/api/auth/logout`   | CSRF + session required; revokes the session, clears cookies |
| GET    | `/api/auth/me`       | Current admin; `401` when missing/expired/revoked, `403` when disabled |

### Storage + Media (Phase 3)

Layering: `media router → media service → storage provider` and
`media service → image processing → storage provider → Mongo`.

#### StorageProvider abstraction (`app/storage/`)

Application code never touches boto3 or the filesystem. Everything goes
through the async `StorageProvider` interface.

```text
Media Service
     ↓
StorageProvider
     ├── LocalStorageProvider   (app/storage/local.py)
     └── S3StorageProvider      (app/storage/s3.py)
```

- Interface: `put(key, data, content_type)`, `get(key)`, `delete(key)`,
  `exists(key)`, `url(key)`, plus a `mode` property. Blocking I/O is wrapped
  with `asyncio.to_thread`.
- **Local** (`STORAGE_MODE=local`, default): objects are files under
  `STORAGE_LOCAL_DIR` (relative paths resolve to the repository root, e.g.
  `storage-local/`, which is git-ignored). Keys are validated before any
  filesystem access; writes are atomic (temp file + `os.replace` + `fsync`);
  deletes are idempotent. `url()` returns a provider-native relative reference
  that is **not** mounted as a public directory.
- **S3** (`STORAGE_MODE=s3`): objects live in `AWS_S3_BUCKET` via boto3 using
  `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION`. The bucket is
  never made public; `url()` returns a pre-signed URL that expires, and the app
  still serves files through its controlled route. S3 failures are wrapped as
  `StorageError` without ever leaking credentials. **Tests use mocks — no real
  AWS credentials or buckets.**
- **Selection** happens once, in `get_storage_provider()` (`app/storage/__init__.py`),
  driven by `STORAGE_MODE`. Missing S3 configuration raises `ConfigurationError`
  at startup (fail fast); an invalid mode is rejected by the settings `Literal`.

#### Object keys

Generated, never user-controlled:

```text
media/{YYYY}/{MM}/{sha256-of-upload}/original.webp
media/{YYYY}/{MM}/{sha256-of-upload}/thumb.webp
media/{YYYY}/{MM}/{sha256-of-upload}/md.webp
media/{YYYY}/{MM}/{sha256-of-upload}/lg.webp
```

Keys use safe characters only, are traversal-safe (validated by
`validate_object_key`), collision-resistant (content hash) and independent of
the original filename. The uploaded name is stored as display-only
`original_name` and never becomes a path.

#### Image processing (`app/modules/media/processing.py`)

Only JPEG, PNG and WebP are supported (detected from the file's actual bytes;
filename extension and Content-Type are ignored). GIF/SVG/HEIC/PDFs are
rejected. The pipeline:

```text
size limit (PRODUCT_IMAGE_MAX_BYTES) → empty check → content hash
→ magic-byte detection (JPEG/PNG/WebP) → Pillow decode (integrity)
→ orientation normalization (EXIF transpose) → pixel-count guard
→ metadata/EXIF stripped → convert to RGB/RGBA → WebP variants
→ store objects → create MongoDB media document
```

- All variants are **WebP** (lossless when the source had alpha) and never
  upscaled (Pillow `thumbnail()` preserves aspect ratio). Dimensions:
  `original` = normalized full size, then `thumb`/`md`/`lg` bounded by
  `MEDIA_THUMB_SIZE` / `MEDIA_MD_SIZE` / `MEDIA_LG_SIZE`.
- `Image.MAX_IMAGE_PIXELS` is set to `MEDIA_MAX_IMAGE_PIXELS` before decoding,
  so crafted huge-dimension headers are rejected early (`422 IMAGE_TOO_LARGE`).
- **De-duplication**: the SHA-256 checksum of the uploaded bytes is stored; a
  compound unique index on `checksum + storage_mode` means re-uploading
  identical content in the same mode returns the existing media record with
  `200` instead of creating a new one.

#### Media model (`app/models/media.py`, `media` collection)

Stores `original_name`, `format` (detected source), `mime_type` (detected), a
`media_type` (`image`), `size_bytes` (upload), dimensions, `checksum`,
`storage_mode`, `object_key` (original variant), the `variants` list (name,
object_key, dimensions, size_bytes, mime_type), `created_by`, `created_at`,
`updated_at`. Indexes (created by `ensure_indexes()` at startup, no manual
step): unique `checksum + storage_mode`, `created_at` (desc), `media_type`.

#### Media API (`app/modules/media/`)

| Method | Path                    | Auth / CSRF                         |
|--------|-------------------------|-------------------------------------|
| POST   | `/api/media`            | `require_role("editor")` + CSRF     |
| GET    | `/api/media`            | any authenticated admin             |
| GET    | `/api/media/{id}`       | any authenticated admin             |
| GET    | `/api/media/{id}/file`  | any authenticated admin (variant query param) |
| DELETE | `/api/media/{id}`       | `require_role("admin")` + CSRF      |
| GET    | `/api/public/media/{id}`| none — public, read-only (Phase 8)  |

- **Upload**: every request is bounded by `PRODUCT_IMAGE_MAX_BYTES`
  (read in streaming chunks to reject oversize early). Responses use clean
  Pydantic schemas — never raw documents, filesystem paths or credentials —
  and expose `urls` pointing at the controlled file route
  (`/api/media/{id}/file?variant=…`), which serves both storage modes.
- **Listing**: pagination (`page`, `page_size` ≤ 100) with `total` and `pages`,
  sorted newest-first by default (`sort=oldest` reverses).
- **File serving**: the variant name is validated against the media document —
  arbitrary object keys are never accepted from callers.
- **Deletion** (`owner`/`admin`): the service deletes every stored variant
  first; only when all succeed is the document removed. Partial failure returns
  `500 STORAGE_DELETE_FAILED` and keeps the record so a retry can converge
  (provider deletes are idempotent).
- **Cleanup**: if storing objects or creating the document fails partway, all
  successfully-created objects are deleted before a `500` is returned — a
  failed upload never leaves orphaned objects or a dangling document.

#### Configuration

New variables: `MEDIA_MAX_IMAGE_PIXELS`, `MEDIA_THUMB_SIZE`, `MEDIA_MD_SIZE`,
`MEDIA_LG_SIZE`. Existing names preserved: `STORAGE_MODE`,
`STORAGE_LOCAL_DIR`, `PRODUCT_IMAGE_MAX_BYTES`, `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_S3_BUCKET`. All names are
documented in the repository-root `.env.example`; the real `.env` is never
modified.

#### Public media delivery (Phase 8)

`GET /api/public/media/{id}?variant=…` (`app/modules/media/public.py`) is the
only unauthenticated media surface. It resolves strictly through the media
document (ObjectId-validated id; variant name cross-checked against the
document's variant list — `original`/`thumb`/`md`/`lg`), streams bytes from
whichever provider stored them, and never accepts object keys, bucket names,
paths, uploads or deletes (other methods return `405`). The admin file route
is untouched and still requires authentication.

- **Semantics**: every media record is publishable by design — only
  authenticated admins can create media, and media exists to be referenced
  from published content. No per-asset visibility flag was added; the smallest
  safe mechanism is id-gated public delivery of admin-approved assets.
- **S3**: the bucket stays private. Public delivery streams through the
  application (`provider.get`), never via public bucket policy or permanent
  public objects. `S3StorageProvider.url()` (short-lived presigned URLs)
  remains available for future direct-serving needs but is not used yet.
- **Caching**: `Cache-Control: public, max-age=31536000, immutable` — variant
  payloads are content-addressed and stable per id+variant. Admin (private)
  responses keep `private` cache headers.
- **Frontend**: `resolveMediaUrl(id, variant)` (`web/src/lib/utils/mediaUrl.ts`)
  is the single public-media mechanism; record-form `resolveMediaUrl(media)`
  still serves the admin UI via the authenticated route. `MediaTile` renders
  the image with placeholder fallback (`onError` → placeholder, never a broken
  icon); client logos/covers, testimonial avatars, branding logo, favicon and
  OG image resolve the same way.

#### SEO, sitemap, robots (Phase 8)

- **Backend**: `GET /sitemap.xml` and `GET /robots.txt`
  (`app/api/routes/seo.py`, mounted without the `/api` prefix; also proxied
  by the Vite dev server). URLs derive from `FRONTEND_URL` — never localhost.
  The sitemap lists the static public routes (`/`, `/projects`, `/activities`,
  `/clients`, `/testimonials`, `/about`, `/contact`, plus `/careers` when
  enabled) and published project/activity/member/work slugs (real slugs; no
  admin, drafts, archived, login, maintenance or media routes). `robots.txt`
  allows crawling, disallows `/admin` and `/admin/*`, and references the
  sitemap. Both return `503` when `FRONTEND_URL` is unset (deployment
  misconfiguration, fail-fast).
- **Crawler HTML**: the `/share/*` routes render standalone Open Graph /
  Twitter documents (and 1200x630 preview images) for member, project and work
  URLs so social crawlers that ignore the SPA still read real metadata.
- **Frontend**: the existing `usePageMeta` system extended with `ogUrl`
  (defaults to canonical), `robots`, and twitter-card mirrors. Canonical/OG
  URLs are domain-aware: `getSiteOrigin()` prefers the configured
  `VITE_SITE_URL` production origin and otherwise falls back to a real
  (non-localhost) runtime origin, returning `null` rather than publishing a
  localhost URL — callers then omit the tag. `absolutePageUrl(path)` builds
  canonicals and share-image URLs from that origin.
- **Robots defaults** (`defaultRobotsForLocation`): private prefixes
  (`/admin`, `/member`, `/setup`) and per-ID verification documents
  (`/verify-certificate`, `/verify-activity-certificate`) default to
  `noindex, nofollow`; 404 and maintenance set it explicitly. Public routes
  emit no stray robots directive unless a page opts in.
- **JSON-LD**: `useJsonLd` injects `Organization` + `WebSite` (home,
  settings-driven only), `CreativeWork` (project and work detail),
  and `Person` (member profile) via textContent serialization — no
  `dangerouslySetInnerHTML` anywhere.

#### Testing strategy

- **Local provider**: real filesystem on a temp directory — round-trips,
  traversal rejection, safe keys, idempotent delete, no escape from root.
- **S3 provider**: fully mocked boto3 client — put/get/exists/delete, URL
  generation, not-found mapping, failure wrapping, no credential leaks.
- **Image pipeline**: real Pillow — accepted formats, renamed text/corrupt/
  truncated rejection, EXIF stripping, orientation normalization, aspect
  ratio, no upscaling, checksum, decompression-bomb rejection.
- **Media API**: the ASGI `client` fixture wipes the `admins`/`media`
  collections **and** the isolated local storage directory before every test;
  uploads use real local providers. Test doubles cover partial-failure cleanup
  and delete failure (document preserved). No real AWS access, ever.

### Content APIs (Phase 4)

Storage "owns the bits" (media objects); content "owns the meaning" — the
entities the public website renders. Content entities reference media by
`media_id` only; content APIs never accept or store files.

#### Shared primitives

- **Slugs** (`app/core/slugs.py`): `slugify()` lowercases and normalizes to
  `[a-z0-9-]`; `validate_slug()` rejects anything else. Invalid user-supplied
  slugs return `422 INVALID_SLUG`.
- **Pagination** (`app/core/pagination.py`): `page`/`page_size` (≤
  `MAX_PAGE_SIZE` = 100), cursor-free offsets returning
  `items/total/page/page_size/pages`. `resolve_sort()` whitelists sort fields
  per entity — an unknown field returns `422` (this is the primary defence
  against query/sort injection; MongoDB operators never appear in query dicts
  because filters are built only from explicitly declared `Query` parameters).
- **References** (`app/services/references.py`): `require_media_exist` and
  `require_client_exists` verify `ObjectId` fields against existing documents
  (`400 INVALID_MEDIA_REFERENCE` / `INVALID_CLIENT_REFERENCE`). Media is never
  deleted when content still references it (orphan references are prevented at
  write time, not swept later).

#### Singletons: settings and branding

Exactly one document each (`unique` unique index on `singleton`). Four rules:

1. **GET never persists** — until the first write, GET returns an in-memory
   default with `id="default"`, so reads stay side-effect free.
2. **PUT replaces** — absent sections reset to defaults; creates the document on
   first write via a race-safe `update_one(..., upsert=True)` on the unique
   `singleton` key (a `DuplicateKeyError` is retried once and then surfaced).
3. **PATCH merges** section-by-section; nested `social.urls` extends at the key
   level and an empty string clears a key.
4. **Public subset**: `/api/public/settings` exposes only
   `general/contact/social/footer/seo` — analytics identifiers and
   `maintenance_mode` are admin-only and never serialized publicly. Public
   branding is purely presentational (colors, mode, media ids).

Admin identity is reused unchanged: reads require `get_active_admin`, writes
require `require_role("editor")` **and** the double-submit CSRF header (a missing
`X-CSRF-Token` yields `403 CSRF_MISSING`; a valid token without a session yields
`401 NOT_AUTHENTICATED`, matching the Phase 2/3 dependency ordering).

#### Clients, projects, testimonials

Each entity has a domain model (`app/models/`), repository (Motor + upserts),
service (business rules), admin router and a public router. Collections,
indexes and per-test wiping of the new collections are registered in
`app/db/indexes.py` and `tests/conftest.py`.

- **Clients** (`clients` collection): a portfolio/partner entity. Publically
  lists every client by **slug**; served projects are published-only and
  embedded as `{slug, name}` refs. `featured` and `display_order` drive the
  ordering. A client referenced by any project or testimonial **cannot be
  deleted** — `409 CLIENT_IN_USE` with a count in the message (no cascades).
- **Projects** (`projects` collection): `status ∈ draft|published|archived`,
  `project_type ∈ client-work|product|experiment`. Public exposure is
  **published-only**: drafts/archived 404 by slug and are excluded from lists;
  `client_id` resolves to a public `{slug, name}` ref (admin responses include
  the internal id). Filters: `category`, `project_type`, `featured`, `status`
  (admin). Sort whitelist: `display_order`, `created_at`, `completion_date`,
  `name`.
- **Testimonials** (`testimonials` collection): `published` gates **all**
  public exposure — unpublished items are excluded from lists and single lookups
  404 (their Mongo id is the public key). `featured` floats items to the top of
  the default listing (`featured desc, display_order asc, created_at asc`)
  and, as `featured`, remains filterable. Fields: `person_name`,
  `testimonial_text`, `role`, `company`, `rating`, `client_id` (→ public
  `{slug, name}` ref), `profile_image_media_id`, `date`.

Slug behaviour is uniform across clients and projects: generated from `name` on
create unless supplied; collisions auto-suffix (`-2`, `-3`, …) for generated
slugs but conflict (`409 SLUG_TAKEN`) when explicit; slugs never mutate on
name-only updates.

New routes mounted in `app/main.py` (all under `/api`):
`/settings`, `/branding`, `/clients`, `/projects`, `/testimonials` and their
`/public/*` counterparts.

#### Phase 4 tests

`tests/test_settings.py`, `tests/test_branding.py`, `tests/test_clients.py`,
`tests/test_projects.py`, `tests/test_testimonials.py`,
`tests/test_content_security.py` (plus `tests/_content_helpers.py`, not
collected) cover: singleton GET-never-persists and PUT/PATCH semantics, slug
normalization/collisions, filter/pagination/sort behaviour, reference
validation, delete-blocking, RBAC/CSRF exposure, published-only public rules,
the featured-first ordering, and public-response safety (no internal ids,
no admin-only fields, no operator/sort injection).

## 3. Frontend

Implemented in `web/`:

- **React 19** + **TypeScript** (strict) + **Vite 7** dev server on port 5173.
- **React Router 7** client routing.
- **API client** (`src/lib/api.ts`): small typed `api.get()` helper over
  `fetch`, base URL from `VITE_API_URL` (default `/api`). Auth/CSRF handling is
  deferred to the authentication phase.
- **Design tokens** (`src/styles/tokens.css`) plus a base layer
  (`src/styles/globals.css`) with a `prefers-reduced-motion` guard.
- **Current route structure**:

  | Route      | File                       | Purpose                                  |
  |------------|----------------------------|------------------------------------------|
  | `/`        | `src/routes/HomePage.tsx`  | Lab-style hero + live system-status probe |
  | `/admin`   | `src/routes/AdminPage.tsx` | Placeholder for the future admin panel    |
  | `*`        | `src/routes/NotFoundPage.tsx` | 404                                    |

  All routes share `src/components/Layout.tsx` (header, nav, footer).
  `src/components/SystemStatus.tsx` calls `/api/health` and
  `/api/health/ready` to prove the frontend → backend connection.

### Contextual media in forms

Forms reference images by `media_id` and upload them in place through the shared
`ImageUploadField` / `ImageGalleryField` (`src/components/form/ImageUploadField.tsx`)
rather than browsing the global media library. Admin fields upload via
`POST /api/media`; member fields via `POST /api/member/media`. The global
library remains available to admins at `/admin/media`. See
[`IMAGE_UPLOADS.md`](./IMAGE_UPLOADS.md) for usage, formats, size limits,
variants and replace/remove semantics.

## 4. Design system

Design tokens (dark lab palette, amber + teal accents, mono HUD typography,
spacing, easing) were **extracted from** the visual prototype at
`D:\Learning\Projects\thridha-labs\index.html`.

The prototype is a **visual/design reference only** — it is a separate
directory, is not imported by the application, and is not part of the
production codebase. Production styling is implemented as original CSS
variables in `web/src/styles/tokens.css`; future branding controls will
re-declare those variables at runtime.

The `web/src/lab/` folder is reserved for a later, original implementation of
the animated experience (canvas/SVG/scroll engine) — nothing is copied from
the prototype.

### Public homepage — Swiss editorial redesign

The public homepage (`web/src/pages/public/HomePage.tsx`) was rebuilt as a
Swiss editorial composition: an oversized, left-aligned type hero, a
disciplined numeric section rhythm (01 selected work → 02 capabilities →
technology → programmes → 04 collaborators → 05 signal → closing invitation)
and generous negative space, replacing the previous repetitive centered
sections.

- **Animated hero backdrop**: `web/src/components/ui/background-paths.tsx`
  (a Framer-Motion SVG layer adapted from a supposed shadcn/Tailwind source to
  this project's own CSS conventions). It is a purely decorative,
  `aria-hidden`, `pointer-events: none` layer confined to the hero, and it
  renders statically under `prefers-reduced-motion`. Animation durations are
  deterministic per path index (never `Math.random()` in render).
- **Theme integration is mandatory and preserved.** Every homepage color is a
  branding CSS variable (`--color-primary/secondary/accent/background/text`
  and the tokens derived from them). `BrandingProvider` →
  `applyBranding()` sets these at runtime from the `/public/branding` API, so
  the homepage follows every predefined light/dark palette **and** custom
  admin-configured colors. No homepage-only theme exists and no accent is
  hard-coded (guarded by `theme-tokens.test.ts`). The BackgroundPaths strokes
  blend from the same tokens, so they adapt to light and dark palettes.
- **Motion**: reuse the existing IntersectionObserver `Reveal` wrapper for
  section reveals and image/card entrance (opacity + transform only), disabled
  under reduced motion. No scroll hijacking or cursor effects.
- **Dependency**: `framer-motion` (added to `web/package.json`/
  `web/package-lock.json`). It is the only new dependency; no Tailwind or
  shadcn migration was introduced.

## 5. Environment configuration

- The **root `.env`** belongs to the backend/runtime configuration: database,
  CORS, auth, rate limiting, storage, email and frontend URL variables. It
  contains real credentials, is listed in `.gitignore`, and must never be
  committed or printed.
- **`web/.env.example`** documents frontend-safe values only (`VITE_API_URL`).
  Anything shipped to the browser is public by definition.
- **Secrets never reach the frontend.** The browser only ever calls the JSON
  API; JWT secrets, database URIs, cloud keys and SMTP passwords remain
  backend-side, wrapped in `SecretStr`.

## 6. Future architecture

Planned phases (not implemented):

```text
Phase 4 — Content APIs
Phase 5 — Web Foundation
Phase 6 — Public Site
Phase 7 — Admin Panel
Phase 8 — S3 + SEO + Production
Phase 9 — QA + Hardening
```

Design principles carried forward:

- Backend routes are grouped by feature module so future capabilities
  (members, workshops, events) mount as new modules without touching existing
  code.
- Protected endpoints reuse the existing authentication stack: cookie JWT +
  CSRF double-submit via `get_active_admin` / `require_csrf` / `require_role`,
  honoring the existing auth environment variables.
- Media storage goes through a provider abstraction selected by `STORAGE_MODE`
  (implemented in Phase 3; no hardcoded providers). S3 is served via the same
  controlled application route, so buckets can stay private.
- Public reads only ever expose published content; featured/published flags
  drive homepage vs. dedicated-page visibility.
