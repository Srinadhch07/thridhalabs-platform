# Thridha Labs Security Scrutiny

## Audit Metadata

| Field          | Value |
|----------------|-------|
| **Date**       | 2026-10-07 |
| **App**        | Thridha Labs platform (`thridhalabs`) |
| **Environment**| Live backend configured with `DEBUG=false` (production cookie policy `COOKIE_SECURE=true`, `SameSite=None`), `STORAGE_MODE=s3` |
| **Auditor**    | OpenCode Security Audit |
| **Scope**      | Full repository: `backend/` (FastAPI), `web/` (React 19 + TypeScript), root config (`.env`, `.env.example`), `docs/ARCHITECTURE.md`, `README.md`, test suites |
| **Commit**     | No git commits exist; all repository files are currently untracked (no history to review) |

## Executive Summary

The Thridha Labs platform is security-conscious and the overwhelming majority of
cross-cutting controls are implemented correctly and backed by tests: cookie-based
session authn with HMAC-SHA256 JWTs and per-account revocation, double-submit CSRF
on every mutation, database-role-driven RBAC, closed mass assignment on admin
schemas, a content-based image pipeline (magic bytes → Pillow decode → EXIF strip →
WebP transcode → decompression-bomb guard), content-addressed private storage,
uniform error envelopes that never echo submitted values, and published-only public
visibility enforced server-side.

No CRITICAL or HIGH issues were identified. Three MEDIUM, four LOW and four INFO
items were found; they centre on **availability/abuse hardening** (rate limiting,
security headers) and **production-readiness configuration** — not on
confidentiality or integrity of stored data. Two actionable gaps matter most
before a public launch: (1) the login rate limiter is process-local and keyed on
`request.client.host`, which behind a reverse proxy collapses every user into one
bucket and lets anyone trigger a global 15-minute admin login lockout; and (2) the
anonymous testimonial submission endpoint has no rate limiting or abuse controls,
allowing unbounded unauthenticated writes.

**Counts:** Critical 0 · High 0 · Medium 3 · Low 4 · Info 4.

## Severity Definitions

- **CRITICAL** — Exploitable remotely without authentication or with minimal
  friction, leading to account takeover, arbitrary code execution, or direct access
  to sensitive data/credentials.
- **HIGH** — Remotely exploitable with meaningful impact, e.g. gaining capabilities
  that should be confined to trusted administrators, accessing admin-only data, or
  causing sustained service disruption with modest effort.
- **MEDIUM** — Requires specific conditions, elevated skill, or a privileged
  position to exploit; impact is significant but contained (availability, abuse,
  or hardening gaps with real consequences).
- **LOW** — Limited direct impact or exploitation difficulty is high; often
  defense-in-depth or information-disclosure items.
- **INFO** — Informational / operational guidance; not a direct threat but worth
  addressing for posture or hygiene.

---

## Findings

### [MEDIUM] SEC-001 — Login rate limiting is process-local and collapses behind a reverse proxy

- **Location:** `backend/app/services/rate_limit.py`, `backend/app/modules/auth/service.py:26-55` (`_client_key`), `backend/app/main.py:132-135` (uvicorn command)
- **Description:** Failed-login attempts are bucketed per `request.client.host`. The
  limiter is a plain in-memory dict in the app process.
- **Evidence:** `_client_key(request)` returns `request.client.host`; `login_rate_limiter`
  is a module-level singleton; the uvicorn entry point does not enable
  `--proxy-headers` / `--forwarded-allow-ips`. With any reverse proxy/LB in front,
  every client presents the proxy's address, so all users share one failure bucket.
  Counters are also not shared across workers and reset on restart.
- **Impact:** An anonymous attacker can obtain a CSRF token (`GET /api/auth/csrf`),
  submit 5 failed logins, and force a 15-minute `429 RATE_LIMITED` window for **all**
  admins behind the proxy — a renewable, remote denial-of-service on the admin
  console. Splitting attempts across multiple worker processes bypasses the limit
  entirely, so brute force protection is weaker than intended against distributed
  attacks.
- **Exploitability:** High — fully unauthenticated, trivially scripted.
- **Recommendation:** Key the limiter on the real client address as communicated by
  the proxy (`X-Forwarded-For` honoring a trusted proxy allow-list), or move to a
  distributed limiter (Redis) shared by all workers, and add per-account throttling
  as a second dimension. A production deployment must enumerate trusted
  proxy/load-balancer IPs and enable forwarded-headers handling so `request.client`
  reflects the client.
- **Status:** OPEN

### [MEDIUM] SEC-002 — Anonymous testimonial submission endpoint has no rate limiting or abuse controls

- **Location:** `backend/app/modules/testimonials/public.py:90-103`, `backend/app/modules/testimonials/schemas.py:119-160`
- **Description:** `POST /api/public/testimonials` (the only unauthenticated write
  endpoint in the API) accepts an unbounded stream of submissions. No rate limit,
  captcha, token bucket, or content heuristic is applied.
- **Evidence:** The router declares only `require_public_site_available`; the submit
  handler calls `service.submit_testimonial(payload)` directly with no limiting.
  There is intentionally no equivalent of `LOGIN_RATE_LIMIT_*`. Indexes on
  `testimonials` (`published`, `featured`, `display_order`, single-field) do not
  include a compound index matching the public list query
  `{published: true, $or: [{status: approved}, {status: {$exists: false}}]}`
  (`backend/app/modules/testimonials/service.py`, `backend/app/db/indexes.py`).
- **Impact:** Unauthenticated spam/flooding: unlimited document creation in the
  production MongoDB, moderator-queue overwhelm, and public-list query degradation
  as the collection grows (filters/sorts cannot be served from a matching
  compound index). No confidentiality/integrity impact — submissions always land
  pending — but sustained availability and data-hygiene impact is real.
- **Exploitability:** High — anonymous, high-volume, cheap.
- **Recommendation:** Add per-IP (trusted proxy-aware) rate limiting to the submit
  endpoint, a honeypot/captcha or admin-gated visibility option, and a compound
  index on `published + status + display_order + created_at`. Consider trimming or
  expiring stale pending submissions.
- **Status:** OPEN

### [MEDIUM] SEC-003 — Missing security headers (no CSP/HSTS/clicks-protection middleware or edge config)

- **Location:** `backend/app/main.py:78-120` (`create_app` adds only CORS), repo root (no nginx/edge config)
- **Description:** The application sets no `Content-Security-Policy`,
  `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy` or `Permissions-Policy` headers, and no reverse-proxy/edge
  configuration exists in the repository to add them.
- **Evidence:** `create_app()` registers only FastAPI + CORSMiddleware; grep for header
  middleware returns nothing. `web/index.html` contains no CSP meta either (a CSP
  meta cannot include `frame-ancestors` anyway).
- **Impact:** The admin panel (incl. `/admin/login`) is not protected against
  clickjacking/UI-redress via `X-Frame-Options`/CSP `frame-ancestors`; there is no
  HSTS to prevent protocol-downgrade; no `X-Content-Type-Options` hardening against
  MIME sniffing; and no CSP as a defense-in-depth layer should a future injection
  bug appear.
- **Exploitability:** None currently — XSS is well contained by React escaping (no
  `dangerouslySetInnerHTML`/`innerHTML`/`eval` anywhere in `web/src`). This is a
  hardening gap, not an active vuln.
- **Recommendation:** Emit security headers in a small middleware and/or configure
  them at the reverse proxy/edge: `Strict-Transport-Security:
  max-age=31536000; includeSubDomains`, `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY` (or CSP `frame-ancestors 'none'`), `Referrer-Policy:
  strict-origin-when-cross-origin`, a CSP tuned for the Vite build, and
  restrictive `Permissions-Policy`. Add a regression test asserting the headers on
  admin and public responses.
- **Status:** OPEN

### [LOW] SEC-004 — FastAPI interactive docs and OpenAPI schema enabled in production

- **Location:** `backend/app/main.py:81-88`
- **Description:** `docs_url=f"{settings.API_PREFIX}/docs"` and
  `openapi_url=f"{settings.API_PREFIX}/openapi.json"` are always set — there is no
  `DEBUG`/environment condition, so `/api/docs` (Swagger UI) and `/api/openapi.json`
  are reachable in the production configuration.
- **Evidence:** `DEBUG=false` in the live `.env`, yet `docs_url`/`openapi_url` are not
  conditional. Current live responses for these routes return documents.
- **Impact:** Publicly discloses the full API surface (routes, request/response
  schemas, RBAC/status-code documentation) — an aid to targeted scanning/recon of
  the admin API. No secrets or code are leaked.
- **Exploitability:** None — information disclosure aiding reconnaissance only.
- **Recommendation:** Disable in production: pass
  `docs_url=None, openapi_url=None` unless `DEBUG` is true (or serve behind an
  authenticated/admin gate).
- **Status:** OPEN

### [LOW] SEC-005 — No generic 500 exception handler; unhandled errors escape the error envelope

- **Location:** `backend/app/core/errors.py:44-72`
- **Description:** `register_exception_handlers` covers `AppError` and
  `RequestValidationError` only. A non-validation, non-`AppError` exception falls
  through to Starlette's default 500 handling.
- **Evidence:** No `Exception` handler is registered. With `DEBUG=false` the default
  response is a plain-text 500 with no internals, so there is currently no
  information leak in production; internal tracebacks go only to server logs.
- **Impact:** Response-contract inconsistency (some errors aren't the
  `{"error": {...}}` JSON envelope), and if `DEBUG` is ever flipped on (or the app is
  misconfigured), internals could appear in responses. Low active risk.
- **Exploitability:** None today.
- **Recommendation:** Register a final catch-all handler that logs the exception
  server-side and returns the standard envelope with a generic message — never
  echoing exception text to clients.
- **Status:** OPEN

### [LOW] SEC-006 — Public health endpoint discloses deployment environment and exact app version

- **Location:** `backend/app/api/routes/health.py:19-44`
- **Description:** `GET /api/health` returns `environment` (`development`/`production`)
  and `version` (`APP_VERSION`) without authentication or rate limiting.
- **Evidence:** Live `.env` has `DEBUG=false`, so `environment: "production"` is now
  publicly returned, along with `version: 1.0.0`.
- **Impact:** Recon aid — confirms the env to attackers and links the deployed build
  to known-CVE lookups. Low sensitivity.
- **Exploitability:** None.
- **Recommendation:** Keep `/api/health` for liveness (or restrict to internal
  networks / a monitoring allow-list) and drop `environment`/`version` or move them
  behind an internal probe.
- **Status:** OPEN

### [LOW] SEC-007 — Unused SMTP credentials configured in the production `.env`

- **Location:** repository-root `.env` (+ `backend/app/core/config.py:79-84`)
- **Description:** SMTP settings are parsed and validated but there is no email code
  path — grep for `smtplib`/`EmailMessage`/`send_mail` finds nothing; SMTP is only
  referenced in config and a logging docstring.
- **Evidence:** `.env` contains `SMTP_*` values (secret values redacted here);
  `ARCHITECTURE.md` notes SMTP delivery is a later phase.
- **Impact:** A live secret with no consumer. If the mailbox is insecure or the
  account is ever compromised it becomes a low-priority, lightly-monitored
  credential; also increases exposure if `.env` ever leaks.
- **Exploitability:** None through this codebase.
- **Recommendation:** Remove the unused SMTP settings (and rotate the password) until
  email is actually implemented, or wire it up behind TLS (`SMTP_HOST`/`SMTP_PORT`
  already validate shape only).
- **Status:** OPEN

### [INFO] SEC-008 — Dependency CVE scan not automated; dev/test tooling in the production manifest

- **Location:** `backend/requirements.txt`, `package.json`, `web/package.json`
- **Description:** Versions are pinned (e.g. `fastapi==0.121.2`, `pydantic==2.12.4`,
  `bcrypt==5.0.0`, `PyJWT==2.10.1`, `Pillow==12.3.0`, `motor==3.7.1`) and are recent,
  but there is no automated vulnerability audit in CI, and `pytest`/`httpx` live in
  the same requirements file as production dependencies.
- **Evidence:** No CI config exists in the repo; no `pip-audit`/`npm audit` step.
  CVE status could not be independently verified offline during this audit.
- **Impact:** No known vuln identified; gap is detection-only.
- **Exploitability:** None.
- **Recommendation:** Add `pip-audit` (and `npm audit`) to a CI pipeline, split
  dev/test requirements from production, and re-run the audit with network access
  before launch.
- **Status:** OPEN

### [INFO] SEC-009 — Repository has no git history (no commits exist)

- **Location:** repo root (`.git` present, nothing tracked, git worktree empty)
- **Description:** `git status --short` shows only untracked top-level directories;
  there are no commits, branches or tags. `.gitignore` correctly excludes `.env`,
  `*.env` (except `.env.example`), build artifacts and the local storage dir.
- **Evidence:** `git log` returns nothing; `.env` is verified git-ignored.
- **Impact:** No version-controlled provenance or audit trail for changes, and no
  protected-branch controls.
- **Exploitability:** None.
- **Recommendation:** Create the initial commit (excluding `.env`), add a
  `Dependabot`/renovate config and branch-protection rules; consider enabling the
  repo-level secret scanner.
- **Status:** OPEN

### [INFO] SEC-010 — Production environment configuration readiness

- **Location:** repository-root `.env`, `backend/app/core/config.py`
- **Description:** The live `.env` is configured for development, not the public
  launch: `CORS_ORIGINS` contains only `http://localhost:5173,http://localhost:4173`;
  `FRONTEND_URL` is unset; `COOKIE_SAMESITE=none`.
- **Evidence:** Current settings dump (secrets redacted): `CORS_ORIGINS =
  http://localhost:5173,http://localhost:4173`; `FRONTEND_URL = None`;
  `COOKIE_SAMESITE = none`. Because `FRONTEND_URL` is unset, `/sitemap.xml` and
  `/robots.txt` both return `503` by design (`backend/app/api/routes/seo.py:31-35,76-77`).
- **Impact:** With the current config the site cannot be reached cross-origin from a
  production domain and SEO artifacts are unavailable; if deployed as-is the admin
  API would be unreachable from the real site (availability, not security).
  `SameSite=None` requires/permits third-party cookie context and is only needed if
  API and web UI live on different registrable domains.
- **Exploitability:** None.
- **Recommendation:** Before launch set `CORS_ORIGINS` to the exact production
  origin(s), `FRONTEND_URL=https://<public>`, and consider `COOKIE_SAMESITE=lax`
  (with `COOKIE_SECURE=true`) if the web UI and API are same-site. Keep the
  startup cross-field validators in place — they already reject `*`, credentials in
  origins, and `SameSite=None` without `Secure`.
- **Status:** OPEN

### [INFO] SEC-011 — No self-service admin password recovery

- **Location:** `backend/app/modules/auth/`, `backend/app/cli/create_admin.py`
- **Description:** There is no password-change/reset flow. Password choice/rotation
  is only available through the interactive provisioning CLI (hidden prompt; never
  argv), which requires host access.
- **Evidence:** Only `login`, `logout`, `me`, `csrf` endpoints exist under
  `/api/auth`; `create_admin.py` reads the password via getpass.
- **Impact:** Operational friction: losing the owner password requires server access
  to recover. No brute-force or recovery-account risk is added.
- **Exploitability:** None.
- **Recommendation:** Add an owner/admin password-change endpoint (with existing CSRF
  + auth + bcrypt policy) once email delivery exists, and document the CLI recovery
  procedure.
- **Status:** OPEN

---

## Confirmed Controls (verified during this audit, with evidence)

- **Session authn:** HttpOnly `COOKIE_NAME` cookie; HS256 JWT signed with a 32+ char
  secret (`config.py:160-164` enforces length in production); revocation via
  `token_version` bump on logout; `decode_access_token` validates signature/expiry.
- **CSRF:** Double-submit — readable CSRF cookie + `X-CSRF-Token` header compared
  with `secrets.compare_digest` (`deps/csrf.py:33`); applied to login, logout, and
  every mutation endpoint (`deps/csrf.py`, all routers); missing header → `403
  CSRF_MISSING`. Covered by `tests/test_csrf.py`.
- **RBAC/authz:** Role resolved from the **database-fetched** admin record at request
  time, not the (unused) JWT role claim (`deps/auth.py:54-71`, `router.py`
  dependencies). Editor+ writes, admin+ deletes; disabled accounts rejected with
  `403`. Matrix covered by `tests/test_rbac.py` and `tests/test_content_security.py`.
- **No mass assignment:** Admin schemas `extra="forbid"`; public `TestimonialSubmit`
  is `extra="ignore"` and the server forces `pending`/`unpublished`/`unfeatured`
  (`tests/test_testimonial_moderation.py:45-63`).
- **No injection/operator reach:** Query dicts are built only from declared `Query`
  params; `resolve_sort` whitelists fields; `page_size ≤ 100`; `$`-operator keys and
  bogus sort fields are ignored/rejected (`tests/test_content_security.py:59-85`).
- **ObjectId safety:** Invalid/malformed ids map to `404`/`422`, never 500 or
  spills; public single lookups of hidden entities 404 uniformly.
- **Login enumeration:** Unknown-email and wrong-password produce byte-identical
  `401 INVALID_CREDENTIALS`; a bcrypt dummy verify equalizes timing
  (`auth/service.py:57-76`). Account enumeration requires a disabled account check
  that is distinct (`403 ACCOUNT_DISABLED`) — acceptable.
- **Image pipeline:** Size-capped streaming read (5 MB) → magic-byte detection →
  Pillow decode+load → `Image.MAX_IMAGE_PIXELS` bomb guard (40 MP) → EXIF/ICC strip
  → orientation normalize → WebP variants, never upscaled. Content-addressed keys,
  `validate_object_key` traversal guard, atomic local writes, private S3 with
  short-TTL presigned URLs, no credential leakage in errors/logs.
- **Public exposure rules:** published-only projects/testimonials; drafts/archived
  and pending/rejected 404/list-excluded server-side; public responses drop internal
  ids and admin-only fields (verified by `tests/test_content_security.py:15-41`).
- **Maintenance mode:** `require_public_site_available` 503s public content/media
  (not admin/auth/health/sitemap by design); public submissions are also gated.
- **XSS surface:** No `dangerouslySetInnerHTML`/`innerHTML`/`eval` in `web/src`; JSON-LD
  injected via `textContent`; external links use `target="_blank" rel="noreferrer"`.
- **Frontend secret handling:** Only `VITE_API_URL` is used from env; auth state from
  HttpOnly cookie only; no JWT in `localStorage`.

## Areas Not Verifiable in This Audit

- CVEs against the pinned dependencies (no offline vulnerability database; see
  SEC-008).
- TLS termination, security headers and bot filtering at the edge/reverse proxy
  (no deployment config exists in the repo).
- MongoDB network exposure, authentication, and user privileges (app uses `MONGO_URI`
  with embedded credentials; only app-level hardening could be reviewed).
- S3 bucket policies / public ACLs / access logs at the AWS console level.
- Reverse-proxy/load-balancer configuration needed to assess SEC-001 properly.

---

# Recommended Remediation Plan

## Immediate (Critical / High)

No CRITICAL or HIGH issues were identified; no immediate-risk remediation is required
before other work. Proceed to the *Before Launch* batch.

## Before Launch (Medium)

1. **SEC-001 — Distributed, proxy-aware login rate limiting.** Use a trusted-proxy
   allow-list and honor the real client IP, or move to a shared/Redis limiter; add
   per-account throttling alongside per-IP. Deploy with forwarded-header handling and
   enumerate trusted proxy IPs.
2. **SEC-002 — Abuse controls on public submissions.** Add per-IP rate limiting to
   `POST /api/public/testimonials`, plus a honeypot field and/or captcha; add a
   compound index `published + status + display_order + created_at`. Consider
   submission limits per (IP, day) and stale-pending cleanup.
3. **SEC-003 — Security headers.** Add HSTS, `X-Content-Type-Options: nosniff`,
   `X-Frame-Options: DENY`/CSP `frame-ancestors`, `Referrer-Policy`,
   `Permissions-Policy`, and a CSP tuned to the Vite build — in middleware and/or at
   the edge. Add a header regression test.
4. **SEC-010 — Correct production env.** Set `CORS_ORIGINS` to the real origin(s),
   `FRONTEND_URL` to the public URL (unblocks sitemap/robots), and review
   `COOKIE_SAMESITE` (`lax` preferred when same-site).

## Hardening (Low / Info)

5. **SEC-004 — Disable `/api/docs` + `/api/openapi.json` in production** (gate on
   `DEBUG` or an admin-only route).
6. **SEC-005 — Register a catch-all `Exception` handler** returning the standard
   envelope (log-only internals).
7. **SEC-006 — Trim `/api/health`** (drop `environment`/`version`) or restrict to
   internal probes.
8. **SEC-007 — Remove/rotate unused SMTP credentials** until email is implemented.
9. **SEC-008 — Add `pip-audit`/`npm audit` to CI**; split dev/test requirements;
   re-run this audit with network access before the public launch.
10. **SEC-009 — Create the initial commit** (`.env` excluded), add dependency-bot and
    branch protection, enable repo-level secret scanning.
11. **SEC-011 — Add a password-change endpoint** when email delivery lands; document
    the CLI recovery procedure.