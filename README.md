# Thridha Labs

Thridha Labs is a technology lab and digital company. We experiment with
intelligence — building websites, digital platforms and products that turn AI,
software and ideas into things people can actually use. Phase 1 of this
repository also covers client work: platforms built for client businesses based
on their requirements.

## Current phase

The repository is currently in:

```text
Phase 4 — Content APIs
```

The foundation (FastAPI backend, MongoDB connection, health endpoints, React +
Vite frontend, test/build tooling), admin authentication (bcrypt password
hashing, JWT sessions in HttpOnly cookies, CSRF double-submit protection,
role-based access control, login rate limiting, interactive admin provisioning
CLI), the storage/media foundation (a store-agnostic `StorageProvider`
abstraction with local disk and S3-compatible backends, a secure image upload
pipeline, content-hash de-duplication, and a paginated authenticated media
library API), and now Phase 4's content APIs: site-wide settings and branding
singletons (with a safe public subset), plus full admin and public APIs for
clients, projects and testimonials — slugs with collision handling, reference
validation, publishing rules enforced server-side, and pagination/filtering/
sorting. The public website and the admin panel arrive in later phases.

## Architecture

```text
React + TypeScript + Vite
        ↓
     FastAPI
      ↓       ↓
  MongoDB   Storage (local disk or S3)
```

Later phases add the public website (built on the public content endpoints) and
the admin panel. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Repository structure

```text
thridhalabs/
├── .env          # Runtime configuration — SECRETS, never committed
├── backend/      # FastAPI application, config, MongoDB layer, pytest suite
│   ├── app/
│   ├── tests/
│   ├── requirements.txt
│   └── pytest.ini
├── web/          # React 19 + TypeScript + Vite frontend
│   ├── src/
│   ├── .env.example   # Frontend-safe values only
│   └── vite.config.ts
├── docs/         # Architecture documentation
├── package.json  # Root convenience scripts (dev, test, build)
└── .gitignore    # Protects .env and build artifacts
```

## Requirements

| Tool      | Version |
|-----------|---------|
| Python    | 3.14+   |
| Node.js   | 24+     |
| npm       | 11+     |
| MongoDB   | any reachable instance (connection configured via `MONGO_URI`) |

## Installation

Backend (isolated virtual environment):

```bash
python -m venv backend/.venv
backend/.venv/Scripts/pip install -r backend/requirements.txt   # Windows
# source backend/.venv/bin/activate && pip install -r backend/requirements.txt  # Unix
```

Frontend:

```bash
npm --prefix web install
```

Root scripts:

```bash
npm install
```

## Running

Start backend and frontend together:

```bash
npm run dev
```

Individually (activate `backend/.venv` first for the backend command):

```bash
npm run backend     # FastAPI on http://127.0.0.1:8000
npm run frontend    # Vite dev server on http://localhost:5173
```

The dev server proxies `/api` to the backend, so the app is same-origin in
development.

## Admin accounts

Admin accounts are provisioned interactively — the password is read from a
hidden prompt and is never passed on the command line:

```bash
npm run admin:create
# or, from backend/ with the virtualenv active:
python -m app.cli.create_admin --role owner
```

Roles are `owner` (highest), `admin` and `editor`; endpoints protected by
`require_role(...)` enforce the hierarchy.

## Media & storage

Media uploads are stored through a provider abstraction selected by
`STORAGE_MODE`:

- **`local`** (default) — files under `STORAGE_LOCAL_DIR` (default
  `storage-local/`, git-ignored).
- **`s3`** — S3-compatible object storage via boto3 using the `AWS_*`
  environment variables. The bucket stays private; objects are served through
  the app's controlled route.

Only **JPEG, PNG and WebP** images are accepted, validated from their actual
bytes (never from the filename or Content-Type). Every upload is decoded by
Pillow, stripped of EXIF/metadata, normalized for orientation, and stored as
**WebP** variants (`original`, `thumb`, `md`, `lg`) — never upscaled, aspect
ratio preserved. Files larger than `PRODUCT_IMAGE_MAX_BYTES` and images whose
pixel count exceeds `MEDIA_MAX_IMAGE_PIXELS` are rejected.

Identical re-uploads are detected with a SHA-256 checksum and re-use the
existing record instead of duplicating storage.

Media API (authenticated; upload/delete additionally require the CSRF header):

| Method | Path                   | Access |
|--------|------------------------|--------|
| POST   | `/api/media`           | editor+ & CSRF |
| GET    | `/api/media`           | authenticated admins |
| GET    | `/api/media/{id}`      | authenticated admins |
| GET    | `/api/media/{id}/file?variant=v` | authenticated admins |
| DELETE | `/api/media/{id}`      | admin+ & CSRF |

Delete removes every stored variant before the metadata document, so a partial
storage failure never silently "succeeds". See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design.

## Content APIs

Phase 4 adds the content model behind the public website. Content entities
reference media assets by id (uploaded through `/api/media`) — content APIs
never accept or store files.

**Singletons** — site-wide settings and branding are single documents:

| Method | Path                | Access       | Behaviour |
|--------|---------------------|--------------|-----------|
| GET    | `/api/settings`      | admin auth   | never writes; returns defaults until first save |
| PUT    | `/api/settings`      | editor+ & CSRF | replace (absent sections reset to defaults), creates on first write |
| PATCH  | `/api/settings`      | editor+ & CSRF | merge |
| GET    | `/api/public/settings` | public      | safe subset: general/contact/social/footer/seo only |
| GET    | `/api/branding`      | admin auth   | same singleton semantics |
| PUT    | `/api/branding`      | editor+ & CSRF | replace |
| GET    | `/api/public/branding` | public    | colors, mode, media ids |

Admin-only settings (analytics identifiers, `maintenance_mode`) are never
serialized publicly.

**Clients, projects, testimonials** — full CRUD behind `/api` (list/get require
admin auth; create/update require editor+ and CSRF; delete requires admin+ and
CSRF) and read-only, unauthenticated under `/api/public`:

| Entity       | Public exposure                          | Access by          |
|--------------|------------------------------------------|--------------------|
| Clients      | all, via `slug`                          | `GET /api/public/clients`, `/{slug}` |
| Projects     | `status == published` only               | `GET /api/public/projects`, `/{slug}` |
| Testimonials | `published == true` only (id is the public key) | `GET /api/public/testimonials`, `/{id}` |

Publishing rules are enforced server-side, never by the frontend: drafts and
archived projects 404 publicly, unpublished testimonials never appear and single
lookups 404 too, and public responses never expose internal Mongo ids (clients
and projects identify by slug) or admin-only fields.

Slugs are normalized (`slugify`), generated from the name when omitted, and
collisions get deterministic suffixes (`-2`, `-3`, …); an explicit slug conflict
returns `409 SLUG_TAKEN` and an invalid slug returns `422 INVALID_SLUG`. A
client referenced by any project or testimonial cannot be deleted
(`409 CLIENT_IN_USE`). Media references and project `client_id` references are
validated against existing records on every create/update.

## Testing

```bash
npm run test
```

Runs the backend pytest suite directly:

```bash
cd backend && python -m pytest
```

Tests run against a dedicated `thridha_labs_test` database **and** an isolated
local storage directory, both removed automatically when the run finishes —
the real database and any real storage are never touched. S3 behavior is tested
with mocks only (no AWS credentials, no real buckets).

The suite covers Phase 1–4: health, auth/RBAC/CSRF, media upload pipeline, and
the content APIs (singleton semantics, slug conflicts, reference validation,
publishing rules, public-response safety, pagination/filtering/sorting).

## Build

```bash
npm run frontend:build
```

Type-checks with `tsc --noEmit` and produces a production bundle in `web/dist/`.

## Environment

Configuration is read from the root `.env` file. **Variable names only** (values
are private and must never be documented or printed):

| Category   | Variables |
|------------|-----------|
| App        | `APP_NAME`, `APP_VERSION`, `DEBUG`, `LOG_LEVEL`, `API_PREFIX` |
| Database   | `MONGO_URI`, `MONGO_DB_NAME`, `MONGO_TIMEOUT_MS` |
| CORS       | `CORS_ORIGINS` |
| Auth       | `JWT_SECRET`, `JWT_ACCESS_MINUTES`, `COOKIE_NAME`, `CSRF_COOKIE_NAME`, `COOKIE_DOMAIN`, `COOKIE_SECURE`, `COOKIE_SAMESITE` |
| Rate limit | `LOGIN_RATE_LIMIT_MAX`, `LOGIN_RATE_LIMIT_WINDOW_MINUTES` |
| Storage    | `STORAGE_MODE`, `STORAGE_LOCAL_DIR`, `PRODUCT_IMAGE_MAX_BYTES`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_S3_BUCKET` |
| Media      | `MEDIA_MAX_IMAGE_PIXELS`, `MEDIA_THUMB_SIZE`, `MEDIA_MD_SIZE`, `MEDIA_LG_SIZE` |
| Email      | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` |
| Frontend   | `FRONTEND_URL` |

The frontend reads only `web/.env.example`-style variables (`VITE_API_URL`),
which are safe to expose. Secrets never reach browser code.

## Security

- **`.env` must remain private.** It holds real credentials and is excluded
  via `.gitignore` — never force-add it, never commit it.
- **Secrets must never be committed** — no JWT secrets, database credentials,
  cloud keys or SMTP passwords in source, docs, logs or commit history.
- **Production uses secure cookie configuration** (`COOKIE_SECURE=true`,
  `SameSite=None` requires `Secure`); the backend refuses to start with an
  invalid production cookie policy.
- **CORS stays allow-listed.** `CORS_ORIGINS` must list exact origins and must
  never contain `*`; credentials are enabled for the future cookie auth.
- **Credentials are backend-only.** Anything in `web/` is public — never place
  secrets in frontend code or frontend environment files.
- **Passwords are hashed with bcrypt** and never appear in responses, logs or
  command-line arguments; login responses are generic (`401 INVALID_CREDENTIALS`)
  for unknown emails and wrong passwords alike.
- **Sessions are HttpOnly cookies.** The JWT cookie is not readable from
  JavaScript; every state-changing request additionally requires the
  double-submit `X-CSRF-Token` header matching a readable cookie.
- **Logout revokes tokens** by bumping the account's `token_version`, so a
  stolen cookie stops working even before it expires.
- **Logins are rate limited** per client IP (`LOGIN_RATE_LIMIT_MAX` failures
  per window, then `429` + `Retry-After`).
- **Uploads never trust metadata.** Filename extension and Content-Type are
  ignored; only magic-byte detection + Pillow decode accept an image (JPEG /
  PNG / WebP). Files over `PRODUCT_IMAGE_MAX_BYTES` and decompression bombs are
  rejected, EXIF/metadata is stripped, and uploads are stored under generated,
  content-derived object keys — never user filenames.
- **Object storage stays private.** The S3 bucket is not made public; media is
  served through a controlled, validated application route. AWS credentials
  never appear in APIs, logs or responses, and S3 is only ever tested with
  mocks.
