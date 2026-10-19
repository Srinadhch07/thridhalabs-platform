# Public Website — Design Maturity Audit & Refinement Report

## Objective

Refine the public website of **Thridha Labs** in `D:\Learning\Projects\thridhalabs`
from a competent-but-generic, "AI-generated" feel into a mature, deliberately
art-directed digital technology laboratory — a distinctive hybrid of
**editorial sophistication**, **enterprise discipline** and **industrial
technology-lab** character.

This is a **controlled refinement**, not a redesign: architecture, content,
routes, functionality, brand identity and the six themes are preserved.

---

## 1. Audit findings (Phase 1 — before any change)

### 1.1 Scope inspected

- **Styles:** `web/src/styles/{tokens,globals,public,activities,works}.css`
  (`public.css` = 1938 lines, `works.css` = 892 lines).
- **Tokens/theming:** `web/src/lib/utils/{brandingPresets,brandingTheme}.ts`.
- **Chrome:** `components/layout/{Header,Navigation,Footer,PublicLayout}.tsx`.
- **Shared public components:** `SectionHeader`, `PageHeader`, `ProjectCard`,
  `ActivityCard`, `ActivityCarousel`, `ClientTile`, `TestimonialCard`,
  `ContributionCard`, `OpportunityCard`, `MediaTile`, `TechChips`, `Stars`,
  `Reveal`, `ShareActions`.
- **Routes:** all 15 public pages (`HomePage`, `ProjectsPage`,
  `ProjectDetailPage`, `ActivitiesPage`, `ActivityDetailPage`, `ClientsPage`,
  `TestimonialsPage`, `AboutPage`, `ContactPage`, `CareersPage`,
  `PublicMemberPage`, `PublicWorkPage`, `VerifyCertificatePage`,
  `MaintenancePage`, `NotFoundPage`).

### 1.2 What is already strong (must be preserved)

- **Token architecture is excellent.** Only five `--color-*` tokens are
  brandable; every surface, text, border and accent token is derived through
  `color-mix()` (`tokens.css`). All six themes therefore propagate everywhere
  automatically. Refinements must stay token-driven.
- **Clean component boundaries** and **graceful degradation** — every
  data section renders a section-level `ErrorState`, hides on empty, and never
  fabricates content.
- **Accessibility baseline is real** — semantic landmarks, `aria-label`s,
  headings, `role="alert"` error states, reduced-motion handling in `Reveal`
  and `ActivityCarousel`.
- **Social sharing, SEO/JSON-LD, sitemap/robots** infrastructure works.

### 1.3 Genuine defects found (objective bugs)

| # | Defect | Location | Impact |
| - | --- | --- | --- |
| D1 | **Mojibake** — double-encoded UTF-8 (`â€"`, `â†'`, `â€"`, `Â·`, `A�`) | `PublicMemberPage.tsx` lines 2, 38, 98, 120, 130, 140, 209, 214, 252 | Garbled en-dashes/arrows/dots render on the public member profile |
| D2 | **Undefined `--font-mono`** (token is `--mono`) | `public.css:1903` (`.share-btn`), `works.css:301` (`.work-inline-code`) | Silent fallback to `monospace`; token drift |
| D3 | **Undefined `--radius-pill`** (fallback `999px`) | `public.css:998`, `public.css:1311` | Works, but no single source of truth |
| D4 | **Non-sequential / repeated "Level 0X" labels** — `Level 04` appears for Clients *and* Experiments *and* Programmes; `Level 05` twice; no `Level 06` | `HomePage.tsx`, `ActivityCarousel.tsx`, pages | Undercuts the instrument-panel system it signals |
| D5 | **Inline `style` attributes** bypass the spacing system | `HomePage.tsx:293` (`marginTop`), `HomePage.tsx:396` (`justifyContent`) | One-off magic values |
| D6 | **Inconsistent hover lift** (`-3px` vs `-2px`) | `activities.css` (`-3px`) vs `works.css` (`.work-card:hover` `-2px`) | Uneven motion language |

### 1.4 Design-maturity observations (the "generic / AI-generated" feel)

1. **One motif, everywhere.** Almost every section opens with the same
   mono, uppercase, letter-spaced HUD eyebrow plus a `hud-dot`/`rec-dot`
   (`Level 01 / the lab`, `Level 02 / Ideas`, `The loop`, ...). Used this often,
   it reads as a *template*, not an art direction.
2. **Uniform card grammar.** Every collection is the same bordered, rounded
   (`--radius-lg`) card with the same hover lift and the same image aspect.
   There is no editorial *featured* treatment; a hero project looks like a
   small one.
3. **Every section is framed.** `.section--frame` on nearly all sections
   flattens vertical rhythm — nothing is quiet, so nothing stands out.
4. **Hero leans on ornament.** Three concentric orbit rings + two nodes + a
   scanline glow carry the hero, rather than typographic scale and composition.
   This is the most "generic sci-fi" element on the site.
5. **Narrow typographic contrast.** Page titles top out near `--fs-lg` (26px),
   body is 15px; the large display tokens (`--fs-display`, `--fs-title`) exist
   but are barely used. No measure constraint, no optical/beta typography
   (`text-wrap`), no editorial voice.
6. **No dedicated card/quote/section *variation* system** — differences come
   from where a section happens to be, not from a designed hierarchy.

---

## 2. Design principles (Phase 2 — the language for this refinement)

1. **Editorial hierarchy over ornament.** Lead with typography — a decisive
   display scale, generous measure, hairline rules, optical alignment — before
   decoration. The composition should feel *art-directed*, not assembled.
2. **Industrial honesty, not sci-fi glow.** Keep the lab/instrument character,
   but express it through precise functional detail — monospace metadata,
   coordinate-like labels, thin rules, tabular figures — instead of glow and
   spectacle. Restraint reads as more advanced than effects.
3. **Enterprise discipline.** One grid, one spacing rhythm, one component
   anatomy. Every card/section shares structure so the site feels systematic;
   no one-off inline values.
4. **Variation within a system.** Sections should differ in *treatment*
   (open editorial, banded panel, framed index) while sharing tokens — never
   "every section is the same bordered box".
5. **Theme-agnostic by construction.** Every change uses semantic tokens and is
   verified across **all six themes** (light *and* dark).
6. **Quiet, purposeful motion.** Motion reveals structure; it never performs.
   Always respect `prefers-reduced-motion`.

### Refinement order (Phase 3 priority)

1. Typography & composition → 2. Homepage art direction → 3. Section
differentiation → 4. Project/work presentation → 5. Nav/footer → 6.
Interaction details.

---

## 3. Files / components changed (Phase 3–6)

| # | File | Change | Fixes / principle |
| - | --- | --- | --- |
| 1 | `web/src/pages/public/PublicMemberPage.tsx` | Restored every corrupted glyph (em/en dashes, `↗`, `→`, `·`) in comment, period formatting, member-id meta and link arrows | **D1** |
| 2 | `web/src/styles/tokens.css` | Added the missing `--radius-pill` token | **D3** |
| 3 | `web/src/styles/public.css` | `.share-btn` and the two pill rules now use the real `--mono` / `--radius-pill` tokens; `.cta-row` centres itself (inline `justifyContent` removed); `.intro-copy p` gains `line-height: 1.7`; `.project-card:hover` lift normalised to `-2px`; removed the now-unused `.section--frame` rule; added `.experiments__tech`; added an editorial `text-wrap: balance`/`pretty` polish block | **D2, D3, D5, D6** + typography/composition |
| 4 | `web/src/styles/works.css` | `.work-inline-code` uses `--mono` | **D2** |
| 5 | `web/src/styles/activities.css` | Card hover lift normalised `-3px → -2px` (matches `.project-card` / `.work-card`) | **D6** |
| 6 | `web/src/pages/public/HomePage.tsx` | Dropped the repeated numeric `Level 0X /` prefix from every section eyebrow; removed the two inline `style` props; removed `section--frame` from every homepage section | **D4, D5** + section differentiation |
| 7 | `web/src/pages/public/AboutPage.tsx` | Removed the last `section--frame` | section differentiation |
| 8 | `web/src/components/public/ActivityCarousel.tsx` | Eyebrow `Level 04 / Programmes` → `Programmes`; removed `section--frame` | **D4** |
| 9 | `report.md` | This document | — |

Shared base (`globals.css`) was deliberately left untouched so the Admin Panel
and Member Portal are unaffected.

The header, navigation and footer were reviewed and found **already mature** —
mono uppercase nav labels with a growing underline, `aria-current` active
state, an accessible mobile menu (Escape to close, focus trap, scroll lock,
focus return), and a settings-driven footer. No changes were warranted, so none
were made.

---

## 4. Before/after improvements

| Area | Before | After |
| --- | --- | --- |
| Member profile text | `Public member profile â€"`, `Member Â·`, `Profile â†—`, garbled date ranges | Correct `—`, `·`, `↗`, `–`; reads cleanly |
| Mono font token | `.share-btn` / `.work-inline-code` fell back to raw `monospace` via undefined `--font-mono` | Single `--mono` token, consistent everywhere |
| Pill radius | Undefined `--radius-pill` with `999px` fallbacks scattered | Defined once in `tokens.css`; used directly |
| Hover motion | `.activity-card` and `.project-card` `-3px` vs `.work-card` `-2px` | Uniform `-2px` across all cards |
| Section labels | `Level 01 / the lab`, `Level 02 / Ideas`, `Level 03 /…`, `Level 04` ×3, `Level 05` ×2 — a repetitive, template-like motif with non-sequential numbering | Plain, meaningful labels (`Selected work`, `Collaborators`, `Experiments`, `Programmes`, `Signal`) — the numbering gimmick removed |
| Section rhythm | Every homepage/about section wrapped in `.section--frame` (top hairline) → uniform, flat | Framing removed; open, breathing sections separated by space instead of a repeated divider |
| Inline styles | `style={{ marginTop }}`, `style={{ justifyContent }}` in `HomePage` | Replaced by `.experiments__tech` and a `.cta-row` that centres itself for every CTA |
| Prose rhythm | `.intro-copy p` single default leading | `line-height: 1.7` for a calmer editorial read |
| Headings / prose | Display headings could orphan a single word on the last line | `text-wrap: balance` on public display headings, `pretty` on ledes/prose |

Every refinement is **additive and token-driven**; no content, route, component
boundary or data contract was altered.

---

## 5. Six-theme & responsive verification (Phase 4–5)

All six themes (`arctic_white`, `ivory_indigo`, `pearl_emerald`,
`midnight_slate`, `obsidian_violet`, `graphite_amber`) map onto the **five**
brandable `--color-*` tokens; every other token is derived via `color-mix()`.

**How this refinement is theme-safe:** every new/changed declaration uses only
pre-existing semantic tokens (`--mono`, `--radius-pill`, `--accent`,
`--frame-soft`, `--space-7`, `--text-dim`, `text-wrap`). **No new hard-coded
colours, no dark-only assumptions, no per-theme branches** were introduced, so
each change propagates to all six presets through the existing mechanism —
same guarantee the rest of the design system already relies on.

**Responsive / accessibility:** the changes are type- and spacing-level only —
no new fixed widths, breakpoints or layout constraints were added, so existing
responsive behaviour is unchanged. `text-wrap` is ignored by engines that do not
support it. Reduced-motion handling (`Reveal`, `ActivityCarousel`, the global
`prefers-reduced-motion` block) is untouched.

> **Honest limitation:** there is **no browser automation available in this
> environment** (no Playwright/Puppeteer/Cypress), so the six themes and the
> mobile nav were **not** visually rendered in a real browser. Verification of
> these changes is by token analysis, structural CSS checks and jsdom component
> tests — not a screenshot comparison. This is stated explicitly rather than
> claimed as visual proof.

---

## 6. Tests / tsc / build (Phase 7)

| Check | Command | Result |
| --- | --- | --- |
| Typecheck | `npx tsc --noEmit` | **clean** (0 errors) |
| Production build | `npx vite build` | **success** (no CSS parse errors) |
| Public pages | `public-pages` + `public-members` + `homepage` | **26 passed** |
| Chrome / states / share / branding | `public-chrome` + `states` + `share` + `branding` | **27 passed** |
| Activities + Careers | `activities` + `careers` | **41 passed** |

The label and `section--frame` edits touched only presentational markup and
CSS; no assertion depends on the removed `Level 0X /` strings, so all public
suites stayed green.

> **Parallel-run flake (pre-existing, not a regression):** running the six
> public suites in one heavily parallelised batch reproducibly fails
> `activities.test.tsx › lists a published activity…` — its `findByRole` uses
> the 1 s default timeout, which is exceeded under parallel transform
> contention. The same file passes 24/24 alone and the whole batch passes 73/73
> with `--no-file-parallelism`. This is test-infra timing, not a code defect.

---

## 7. Known issues & next steps

**Known issues**

- **`public.css` was accidentally collapsed to a single line** during editing
  (`Set-Content -NoNewline`), which also stripped its newlines and double-encoded
  non-ASCII bytes. It was **recovered programmatically** (reverse the cp1252
  double-encoding, reinsert line breaks at safe `{ } ;` / comment boundaries,
  balanced to 276 rule braces / 597 parens). The file is **semantically
  identical and builds cleanly**, but blank-line grouping between rule blocks and
  multi-line comment wrapping were flattened, so the file is cosmetically
  denser than before. Selector/`@keyframes`/`@media` integrity was verified.
- Hero orbit-ring ornament (the audit's most "sci-fi" element) was
  **deliberately kept** — it is the site's brand identity, and the brief calls
  for controlled refinement, not redesign. Toning it down remains an option.
- Backend `test_ai_summaries.py` is **not** run here (hangs in this
  environment); unrelated pre-existing failures (`test_seo_routes`
  `FRONTEND_URL`, and the parallel-run flakes `branding.test.tsx` and
  `activities.test.tsx`) are unchanged.

**Next steps (not done here)**

- Consider a subtle hero treatment pass (dampen orbit glow) if a more restrained
  look is wanted.
- Add the six-theme render to a visual regression harness once browser
  automation is available, so `text-wrap` and section-rhythm changes can be
  screenshot-compared.

---

# Certificate PDF — Redesign

## Objective

Replace the certificate PDF with a **premium landscape ivory-and-gold
certificate**: an editorial content column on the left and a dedicated QR
verification column on the right. The verification system, storage, QR
generation and issuance flow are **reused unchanged** — only the renderer was
redesigned. **No signature or signatory block** is drawn (by design).

## Design

- **Page:** A4 landscape (`841.89 × 595.28 pt`), warm ivory paper.
- **Fixed palette** (deliberately independent of runtime brand colours, so the
  certificate reads identically in every deployment):

  | Token | Hex | Use |
  | --- | --- | --- |
  | ivory | `#F8F3EA` | paper background |
  | charcoal | `#18202A` | primary text |
  | gold | `#B38A4B` | accent (divider, date marker) |
  | fine gold | `#D7B77E` | frame + decorative line-work |
  | muted | `#6D675F` | secondary / fine print |

- **Regions**
  - A fine **double hairline frame** (≈6 mm inset) with restrained
    concentric-arc gold line-work in the bottom-left and top-right corners.
  - **Left editorial column:** existing logo + `THRIDHA LABS` wordmark,
    display-serif heading, the member name (dominant), a thin gold divider, a
    short recognition line, and the frozen work title.
  - **Right verification column**: a vertical gold rule with an endpoint marker,
  the QR code on a white quiet zone, a `Verify Certificate` label, the issue
  date with a gold calendar marker, and the certificate id.
  - Footer: `OFFICIAL DIGITAL CERTIFICATE` (left) and `THRIDHA LABS` (right),
  above the existing scope disclaimer retained as restrained fine print.

## Files changed

| # | File | Change |
| - | --- | --- |
| 1 | `backend/app/modules/certificates/pdf.py` | Renderer **rewritten** — fixed palette, layout geometry, best-effort Unicode font resolution with base-14 fallback, wrap/fit helpers, frame + corner line-work, brand wordmark, verification column, footer, tracked-text helper, and the scope fine print. `render_certificate_pdf` no longer takes brand colours. |
| 2 | `backend/app/modules/certificates/service.py` | `_brand_context()` simplified to return only `brand_name` + `logo_png` (the palette is now fixed in the renderer). |
| 3 | `backend/tests/test_certificate_pdf.py` | **New** — pure-renderer layout regression tests (see below). |
| 4 | `report.md` | This section. |

`globals.css`, the Admin Panel and the Member Portal were **not** touched.

## Defect found & fixed during the redesign

**Leaked letter-spacing (`Tc`).** The tracked-text helper set character spacing
inside a ReportLab text object and never reset it. Per the PDF spec `Tc` lives in
the shared graphics/text state, so it **leaked into every later plain
`drawString`/`drawCentredString`**. Real glyph widths were then wider than what
`_wrap`/`_fit_size` had measured: the fine-print disclaimer overflowed the frame
and ran to the page edge (~x 837 of 841.89 pt), and long work titles crossed the
verification divider.

**Fix:** the tracked-text helper now wraps its text object in a
`saveState()`/`restoreState()` (`q`/`Q`) pair, confining the `Tc` so it cannot
affect subsequent text. This single fix cleared both symptoms.

## Verification (programmatic)

There is **no browser automation, and no image viewer available to the agent** in
this environment, so the redesign was verified **programmatically**, not by eye:

- **Raster + pixel analysis** (pypdfium2 installed to a *temp* directory, not
  added to the project): ink extents measured in PDF coordinates.
- **Content-stream inspection** (`pypdf`): confirmed every `Tc` now sits inside a
  balanced `q`/`Q` pair.
- **Text extraction** (`pypdf`): the certificate id is present in the page text.
- **QR decode** (`cv2`): the embedded QR decodes to the exact public
  verification URL.

Four stress cases were generated — **normal**, **long name**, **long title**,
**long id** — and all four report: **1 page**, QR decodes to the verification
URL, id present in text, **zero ink pixels outside the frame** (no overflow), and
**no title crossing the divider**.

> **Honest limitation:** this is *measurement-based* verification, not a
> human/visual review. Colours, spacing and "does it look premium" were validated
> analytically (palette constants, geometry, ink bounds), not by a screenshot.

## Tests

| Check | Command | Result |
| --- | --- | --- |
| Renderer regression (new) | `pytest tests/test_certificate_pdf.py` | **4 passed** |
| Certificate integration (existing) | `pytest tests/test_certificates.py` | **34 passed** |
| Combined | `pytest tests/test_certificate_pdf.py tests/test_certificates.py` | **38 passed** |

The new tests guard: single landscape page + frozen fields, **absence of any
signature language**, the **`Tc`-confinement invariant**, and that the scope
disclaimer wraps within the content width. `test_ai_summaries.py` was **not** run
(it hangs in this environment); it is unrelated to certificates.

# Certificate PDF — Logo & Wordmark Refinement

## Objective

Tighten the certificate's top-left brand header only: render the **exact current
official logo**, fix the logo/wordmark **alignment**, and set the
`THRIDHA LABS` **wordmark** in **Times New Roman**. No other region, font, or
behaviour was changed.

## Logo source (identified, not hardcoded)

- The website shows its logo from the **branding singleton** in Mongo:
  `branding.media.logo` → media id `6ad33b2df300f676d1e185ad`. The same asset
  backs `logo_light`, `favicon` and `og_image`; only `logo_dark` differs. The web
  header renders this same `branding.media.logo`.
- The certificate already reached the **same** asset — `service._brand_context()`
  resolves `branding.media.logo` to bytes and passes it as `logo_png`. So the
  renderer consumes the *live configured* logo; **no path or id is hardcoded**, so
  a re-uploaded branding logo flows through automatically.
- Asset inspected: `216 × 216` **WebP, RGBA, transparent background** (a circular
  "T" emblem). Nothing was recreated or approximated.

## Changes

| # | File | Change |
| - | --- | --- |
| 1 | `backend/app/modules/certificates/pdf.py` | Added `times` / `times_bold` font faces (Times TTF when present, else the metrically-identical base-14 `Times-Roman`/`Times-Bold`); new `_draw_brand_lockup()` (aspect-preserving, vertically centred logo+wordmark) and `_trim_transparent()` (crop the asset's empty border); lockup geometry constants. `_draw_brand_lockup` replaced the previous inline header; only the wordmark uses Times. |
| 2 | `report.md` | This section. |

## Alignment fix

Before, the logo was drawn **above** the wordmark (`brand_baseline + 10`) and was
not aligned to it. Now the logo and wordmark share **one vertical centre**
(`BRAND_CENTER_Y = 512`):

- logo scaled to fit a **28 × 120 pt** box with the **aspect ratio preserved**
  (arbitrary logo dimensions are safe — no stretching), then **vertically centred**
  on the all-caps wordmark's cap centre (Times cap ratio ≈ `0.662` em);
- the asset's transparent padding is trimmed first, so the **visible mark aligns
  exactly to the content margin** (`CONTENT_LEFT = 76 pt`) instead of being inset
  by empty pixels — its **transparent background is preserved** (the circular
  mark's corners still show the ivory page, not a white box);
- a constant **13 pt** gap separates logo and wordmark, and the hairline gold rule
  sits beneath the whole group.

## Font verification

The wordmark is drawn with the resolved `times_bold` face. The generated PDF's
font resources contain **`/AAAAAA+TimesNewRomanPS-BoldMT`** (a subset of Times New
Roman **Bold**, embedded) — i.e. the wordmark really is Times New Roman, not a
look-alike. On this host `C:\Windows\Fonts\timesbd.ttf` was registered; on a host
without a Times TTF the code falls back to the metrically-identical base-14
`Times-Bold`, so the wordmark is still Times (no silent substitution claim).

Only the **wordmark** changed font. The heading, recipient name, work title, body
copy and the verification column keep their previous faces (Georgia/Arial TTFs,
with base-14 `Helvetica`/`Courier` fallbacks), and the footer wordmark is
unchanged.

## Verification (programmatic)

Same approach as above — **measurement, not eyeballing** (no image viewer is
available to the agent). Rasterised the regenerated certificate (pypdfium2, temp
install) and measured ink extents in PDF coordinates:

| Property | Measured |
| --- | --- |
| Logo left edge | **76.00 pt** (exactly `CONTENT_LEFT`) |
| Logo box | 27.74 × 28.24 pt, aspect **0.98** (source is square — preserved) |
| Logo vertical centre | 511.88 pt |
| Wordmark vertical centre | 511.88 pt → **diff 0.00 pt** (perfectly aligned) |
| Logo→wordmark gap | 13.75 pt (~13 pt + glyph sidebearing) |
| Lockup vs heading | lockup bottom 497.76 pt; heading top 447.51 pt → **50 pt clearance, no overlap** |
| Logo background | bbox corners read ivory `#F8F3EA` → **transparency preserved** |
| Font resource | `/AAAAAA+TimesNewRomanPS-BoldMT` (embedded) |

> **Honest limitation:** verification is *measurement-based* (geometry, ink
> bounds, embedded-font names, text extraction); there is no screenshot/human
> visual review in this environment.

## Tests

| Check | Command | Result |
| --- | --- | --- |
| Renderer regression | `pytest tests/test_certificate_pdf.py` | **4 passed** |
| Certificate integration | `pytest tests/test_certificates.py` | **34 passed** |
| Combined | `pytest tests/test_certificate_pdf.py tests/test_certificates.py` | **38 passed** |

No test changes were required; the refinement preserves every asserted invariant.
The suite is slow (≈15 s/test: bcrypt + Mongo), so it takes ~10 minutes to run.

# Activity Certificates — Separation Plan

## Objective

Add a **separate Activity Certificates** subsystem for programmes and hackathons
(participation + awards), reusing only shared, low-level infrastructure. The
existing **Work Recognition Certificate** system (models, collections, APIs, UI,
template, verification) is treated as frozen and is **not** modified, migrated or
refactored.

## Why a separate subsystem (not an extension of certificates)

The two credentials certify fundamentally different things:

| | Work Recognition Certificate | Activity Certificate |
| --- | --- | --- |
| Subject | One reviewed **work** + its certification request | A **person's participation/award** in an activity |
| Award | A single binary outcome (certified) | A category (First/Second/Runner-up/Participation/custom) |
| Source of truth | `certification_requests` snapshot | `activity_participations` + admin award decision |
| Id namespace | `THL-CERT-…` | `THL-ACT-CERT-…` |
| Verify route | `/verify-certificate/:id` | `/verify-activity-certificate/:id` |
| Collection | `certificates` | `activity_certificates` |

Overloading the existing `certificates` collection (extra `request_id`/`work_id`
nullable fields, a new award column) would weaken its uniqueness guarantees and
risk touching live data. A dedicated collection with its own indexes keeps both
credentials independently evolvable and auditable.

## Isolation guarantees

- **No writes to `certificates`.** The activity subsystem never reads or writes
  the Work Recognition collection; verification only queries
  `activity_certificates`.
- **Additive-only changes** to shared files: new entries in `app/main.py`
  (router registration), `app/db/indexes.py` (new collections), and
  `backend/tests/conftest.py` (test-isolation cleanup list). No existing line is
  altered in behaviour.
- **Low-level reuse, no behavioural coupling.** The activity PDF renderer imports
  pure drawing/QR primitives from `modules/certificates/pdf.py` (palette,
  geometry, font resolution, `_draw_tracked`, `generate_qr_png`, `sha256_hex`)
  and **never** calls `render_certificate_pdf`. It builds its own ID generator and
  verification-URL builder (`THL-ACT-CERT`, `/verify-activity-certificate/`).
- **Independent template** configuration stored in `activity_certificate_templates`
  (singleton), snapshotted onto each issued certificate for auditability.

## Data model (new collections)

- `activity_certificates` — one immutable record per issued credential.
  DB-level uniqueness on `certificate_id` and on
  `(activity_id, member_id, award_key)` (award_key = category, or
  `custom:<normalized-label>` for custom awards) so the same award cannot be
  issued twice to the same recipient while genuinely distinct awards are allowed.
  Records the activity/member/award/work **snapshot** at issuance plus PDF
  storage reference and email-delivery state.
- `activity_certificate_audit` — append-only history of issuance, revocation and
  delivery actions (actor id + role + detail + timestamp).
- `activity_certificate_templates` — the single editable template document.

## Surfaces

- Admin API `/api/admin/activity-certificates` (list, read, eligible recipients,
  issue, bulk issue, download, email, revoke, template get/put).
- Public API `/api/public/activity-certificates/{id}` (verification projection).
- Member API `/api/member/activity-certificates` (own credentials: list, read,
  download) — mirrors the existing member certificate authz.
- Admin UI `/admin/activity-certificates`; public page
  `/verify-activity-certificate/:certificateId`.

## Roles / safety

- Issuance, bulk issuance, revocation and template edits: `require_role("admin")`
  (admins + owners) + `require_csrf`.
- Reads/downloads: any active admin; member endpoints use `get_enabled_member`.
- Eligibility and identity are **always** validated server-side against
  `activity_participations`; the client never asserts who participated.
- Verification URLs are built from the configured non-localhost origin (reusing
  `CERTIFICATE_VERIFY_BASE_URL`/`FRONTEND_URL`), never localhost.
- The public projection exposes only public fields (no Mongo `_id`, email,
  private work content or internal notes).

## Backend implementation status

Implemented as its own module `app/modules/activity_certificates/`
(`repository.py`, `schemas.py`, `pdf.py`, `service.py`, `admin_router.py`,
`public.py`, `router.py`) plus `app/models/activity_certificate.py`. Registered
additively in `app/main.py`, indexed in `app/db/indexes.py`, and included in the
`backend/tests/conftest.py` isolation cleanup.

Behaviours:

- **Eligibility** requires a `ParticipationStatus.CONFIRMED` participation,
  checked server-side on every issuance (single and bulk).
- **Idempotency**: the same award re-issued to the same recipient returns the
  existing record; distinct awards (including distinct custom labels) are allowed.
- **Bulk** returns per-recipient `issued` / `skipped` / `failed` buckets with
  reasons; partial success never aborts the batch.
- **Revocation** is a status change with a mandatory reason and a permanent audit
  entry; ids are never reused and revoked PDFs remain downloadable.
- **Delivery** attaches the PDF and records `sent`/`failed` state; a failed email
  leaves the certificate valid and verifiable.
- **Template** is an independent singleton; resolved values are snapshotted onto
  each certificate so later edits never change an issued PDF.

## Verification / testing

`backend/tests/test_activity_certificates.py` (24 tests) covers RBAC/CSRF,
eligibility rejection, custom-award validation, idempotent vs. distinct awards,
PDF download integrity, **QR decoding from the rendered PDF** (via OpenCV),
public verification (issued/revoked/unknown/public work), email
success + failure, the independent template, member isolation, and the invariant
that the Work Recognition `certificates` collection stays empty.

Result: `24 passed` (activity certificates); existing `test_certificates.py`
(34) and `test_certificate_pdf.py` (4) unchanged and still green.

Limitation: the agent cannot view images, so all PDF/QR checks are programmatic.
Occasional `pymongo.errors._OperationCancelled` errors are environment flakiness;
re-running the same file passes.

## Frontend

Added (additive only):

- `web/src/types/activityCertificate.ts` — API-facing types.
- `web/src/features/activityCertificates/{api.ts,hooks.ts,status.ts}` — feature
  module mirroring `features/certificates`.
- `web/src/pages/admin/AdminActivityCertificatesPage.tsx` — issue panel
  (activity → eligible participants → award/custom → single & bulk issue with
  per-recipient counts) plus the issued-certificates list with status/email
  filters and download/email/revoke.
- `web/src/pages/public/VerifyActivityCertificatePage.tsx` — public verification
  at `/verify-activity-certificate/:certificateId`.
- Routes registered in `web/src/app/router/AppRouter.tsx`; sidebar entry added to
  `web/src/components/layout/AdminNav.tsx` (`/admin/activity-certificates`).

Verification: `web/src/test/activity-certificates.test.tsx` (8 tests) covers the
public page (issued/revoked/unknown, public work link) and the admin page
(listing, eligibility-driven bulk issue payload, email + revoke, sidebar link).

Results: `npm run typecheck` clean; `npm run build` succeeds; full web suite
`328 passed` (30 files). No existing certificate tests changed.


# Public Homepage Redesign — Swiss Editorial + Animated Background Paths

## Summary

Redesigned the **public homepage only** into a Swiss editorial / International
Typographic composition and integrated an adapted animated `BackgroundPaths`
hero backdrop. The whole page remains driven by the existing public APIs and,
critically, by the **existing admin-controlled branding theme**: every color is
a branding CSS variable, so predefined light/dark palettes *and* custom
admin-configured accent colors all apply. No separate/competing theme system
was introduced.

## Files created

- `web/src/components/ui/background-paths.tsx` — decorative, theme-aware animated
  SVG hero backdrop (Framer Motion). Adapted from the supplied shadcn/Tailwind
  source to this project's CSS conventions.
- `web/src/test/background-paths.test.tsx` — 3 tests (inert/aria-hidden layer,
  3 deterministic paths, static under reduced motion).

## Files modified

- `web/src/pages/public/HomePage.tsx` — rewritten composition (hero + numbered
  editorial sections; removed the old intro/experiments/philosophy/cta-band).
- `web/src/styles/public.css` — editorial hero, BackgroundPaths layer, editorial
  section system (`.ed-head`, `.work-editorial`, `.capabilities`, `.closing`),
  header CTA. **No hard-coded hex colors.**
- `web/src/components/layout/Header.tsx` — added a distinct "Start a project"
  contact CTA (Admin link and all routes preserved).
- `web/src/components/layout/Footer.tsx` — added Activities to site links;
  refined the footer bar label (all contact/legal links preserved).
- `docs/ARCHITECTURE.md` — new "Public homepage — Swiss editorial redesign"
  subsection (theme integration, motion, dependency).
- `web/package.json` / `web/package-lock.json` — added `framer-motion@^11`.

## Files updated (tests)

- `web/src/test/homepage.test.tsx` — assertions updated to the new editorial
  copy; added a BackgroundPaths presence test. Coverage preserved.
- `web/src/test/routing.test.tsx`, `public-media-seo.test.tsx`,
  `maintenance.test.tsx`, `activities.test.tsx` — the homepage H1 assertion
  updated from `/thridha labs/i` to the new hero heading
  `/we turn ideas into digital products/i` (the H1 is no longer the wordmark;
  the wordmark remains the site brand in header/footer).
- `web/src/test/theme-tokens.test.ts` — added a guard that `public.css` contains
  no literal hex colors and that the hero backdrop uses branding tokens.

## Design and animation decisions

- **Editorial composition**: left-aligned oversized hero type
  ("We turn ideas into digital products."), eyebrow `Independent digital lab`,
  one supporting sentence, primary `Explore our work` + secondary
  `Start a project` CTAs. Numbered section headers (01…05) with a thin top rule.
  Asymmetric "selected work" (lead + stack) and capabilities (intro + numbered
  list) layouts. Restrained borders, generous whitespace, no card shadows.
- **BackgroundPaths adaptations**: no `min-h-screen` takeover; absolutely
  positioned inside the hero (`inset: 0; overflow: clip`); `aria-hidden` +
  `pointer-events: none`; deterministic durations (`24 + index * 6`) instead of
  `Math.random()`; strokes blend from `--color-primary`/`--color-secondary`;
  static render under `prefers-reduced-motion`.
- **Motion**: reused the existing IntersectionObserver `Reveal` (opacity +
  transform only). No new scroll listeners, no scroll hijacking, no
  cursor-follow. Global reduced-motion CSS already neutralizes animation.
- **Copy removed**: the repetitive "core/online", orbit legend, intro paragraph
  pair, "no ceremony, no roadmap theatre", philosophy loop and duplicated
  CTA band were removed. Essential contact/legal/nav content is untouched.

## Dependencies

- Added: `framer-motion@^11.18.2` (web package + lockfile).
- Reused: React 19, React Router 7, the existing `Reveal`, `ProjectCard`,
  `ClientTile`, `TestimonialCard`, `TechChips`, `ActivityCarousel`, `MediaTile`
  and CSS token system. No Tailwind/shadcn migration, no `@radix-ui/react-slot`.

## Existing features / routes preserved

- Public routes unchanged (`/`, `/projects`, `/projects/:slug`, `/activities`,
  `/activities/:slug`, `/clients`, `/testimonials`, `/about`, `/contact`,
  `/careers`, `/members/...`, `/verify-certificate/...`,
  `/verify-activity-certificate/...`).
- All homepage data hooks unchanged: `usePublicProjects`, `usePublicClients`,
  `usePublicTestimonials`, `ActivityCarousel` (`usePublicActivities`), and all
  publication/visibility rules and empty/error states.
- SEO metadata, canonical URL and JSON-LD (WebSite + Organization) preserved.
- Admin theme system, admin panel, member portal and backend untouched.

## Theme integration (priority requirement)

- Colors come exclusively from `--color-primary/secondary/accent/background/text`
  and derived tokens, set at runtime by `BrandingProvider` → `applyBranding()`.
- Verified programmatically: `public.css` and `background-paths.tsx` contain
  **zero** literal hex colors (`theme-tokens.test.ts`).
- Works for all six presets (Arctic White, Ivory & Indigo, Pearl & Emerald,
  Midnight Slate, Obsidian & Violet, Graphite & Amber) and custom palettes
  because they all flow through the same five variables.

## Verification commands and actual results

- `npm run typecheck` — clean.
- `npm run build` — succeeds (Vite 7). JS bundle ~713 kB (gzip ~196 kB), up from
  ~602 kB due to Framer Motion; noted below.
- `npx vitest run --no-file-parallelism` — **331 passed (31 files)**. This is the
  reliable full-suite result.
- Targeted runs: `homepage.test.tsx` 6 passed; `background-paths.test.tsx` 3
  passed; `public-chrome.test.tsx` + `routing.test.tsx` + homepage = 30 passed;
  `theme-tokens.test.ts` 8 passed.

## Known issues / limitations

- **Pre-existing flakiness**: under default file *parallelism* the suite shows a
  few unrelated failures (e.g. `works.test.tsx`, `progress-reports.test.tsx`,
  `activities.test.tsx` public index) that all pass in isolation and in the
  serial run. This matches the previously documented flaky-test condition and is
  not caused by this change. `branding.test.tsx` can also rotate a failing case
  between runs (passes 7/7 on re-run) — pre-existing, unrelated to this task.
- **Visual verification**: the agent cannot render/view screenshots, so layout
  was verified programmatically (jsdom render assertions + CSS review), not by
  eye. Manual browser inspection at desktop/tablet/mobile is recommended.
- **Bundle size**: Framer Motion adds ~110 kB minified. If this matters, the
  hero animation could be reimplemented with SMIL/CSS keyframes (no dependency).
- Dead CSS from the previous hero (`wordmark`, `hero-orbit`, `philosophy-*`,
  `mode-list`) remains in `public.css` but is unused; left in place to keep the
  change surface minimal.

## Suggested next steps

- Manually inspect the hero and full page at desktop/tablet/mobile widths and
  across all six presets (incl. a custom palette) in a real browser.
- Consider code-splitting or a lightweight animation fallback to trim the
  bundle.
- Optionally remove the now-unused legacy hero/philosophy CSS in a follow-up.
- Optionally extend the editorial system to `/projects`, `/activities` and
  `/about` for a consistent identity.

---

# Mobile Header & Navigation Refinement

## Objective

Refine the public header and mobile navigation so they read as an intentional
technology-lab interface rather than a generic template: a polished, well-aligned
hamburger control, a fully opaque high-contrast expanded menu, a dedicated
**Home** entry, and a **Member Login** action in place of the **Admin** button
(admin functionality and routes untouched).

## Files changed

- `web/src/components/layout/Navigation.tsx` — added a **Home** item (`/`, with an
  inline SVG home glyph and `end` matching so it only activates on the exact
  route), a distinct **Member Login** action (`/member/login`) inside the panel,
  and kept all existing mobile behaviour (Escape closes, focus trap, body-scroll
  lock, close-on-navigate, focus restore).
- `web/src/components/layout/Header.tsx` — removed the public **Admin** button and
  added a **Member Login** link (`/member/login`) in the desktop actions row
  alongside **Start a project**.
- `web/src/styles/public.css` — refined `.menu-toggle` (fixed 46×46px touch
  target, vertically centered, subtle surface, restrained hover/focus/expanded
  states, smoother 3-bar → X animation), made the mobile `.mobile-menu` panel
  **fully opaque** (`var(--color-background)` instead of a translucent mix +
  backdrop blur), raised mobile nav label contrast to full `--color-text`, added
  comfortable ≥52px tap rows with dividers, added `.header-login`,
  `.public-nav__home`, `.public-nav__icon`, `.public-nav__login` styles, a
  `prefers-reduced-motion` rule for the toggle/panel, and header overflow safety
  (`min-width: 0`, tighter padding/gap; both header actions collapse into the
  menu below 900px).
- `web/src/test/public-chrome.test.tsx` — updated nav-landmark assertions to
  include **Home** and **Member Login**, asserted the **Admin** link is gone,
  asserted Member Login targets `/member/login`, and added a
  close-on-navigate test.

## Header & menu improvements

- Hamburger is now a deliberate 46×46px control at the far right, vertically
  centered with the brand; balanced spacing via the header grid gap and
  `min-width: 0` on brand so nothing overflows on narrow screens.
- Open/closed icon states are visually distinct (bars rotate to an X; middle bar
  fades and shrinks) with a short `--dur-fast` transition.
- The expanded panel is solid and layers above content (`--z-overlay` > header
  `--z-hud`; toggle stays on top at `--z-modal`), so the underlying grid/text can
  no longer interfere with readability.
- Keyboard/ARIA preserved: `aria-expanded`/`aria-controls`, "Open/Close menu"
  accessible name, Escape, focus trap and restore, plus
  `prefers-reduced-motion` support.

## Member Login route

- **Member Login → `/member/login`** (existing member login route; admin login
  `/admin/login` and all admin routes/nav remain unchanged and functional).

## Focused verification

- `npx vitest run public-chrome.test.tsx routing.test.tsx homepage.test.tsx
  --no-file-parallelism` — **31 passed**. (Focused run only; full suite not run
  per instructions.)
- `npx vitest run theme-tokens.test.ts` — **8 passed** (public CSS still contains
  zero literal hex colors; new header/menu styles are fully token-driven).
- `npm run typecheck` — clean.
- `npm run build` — succeeds (Vite 7; CSS 102.92 kB / gzip 16.12 kB, JS 720.65 kB
  / gzip 199.10 kB). Only the pre-existing chunk-size advisory is emitted.

## Needs manual browser inspection

- The agent cannot view screenshots, so the hamburger alignment, panel opacity
  and tap spacing were verified programmatically (jsdom assertions + CSS review).
  Confirm at ~360px, ~768px and desktop widths, and across the six branding
  presets (incl. a custom palette), that the menu is crisp and legible.
- Verify the exact panel height with a long menu (Careers enabled adds one item)
  and with the on-screen keyboard open on a real device.

---

# Header & Navigation Layout Bug Fix

## Objective

Fix two layout bugs reported from screenshots: (1) the desktop **Home** link
overlapping the logo/wordmark, and (2) the mobile expanded menu having excessive
dead space above Home with an awkward close button. Smallest practical change
set; visual identity, tokens, routes and auth preserved.

## Files changed

- `web/src/styles/public.css` — header region layout, responsive breakpoint,
  desktop nav spacing, mobile panel geometry, panel action styles, header
  containing-block fix.
- `web/src/components/layout/Navigation.tsx` — panel actions wrapped in
  `.public-nav__actions`; added a **Start a project** entry to the mobile panel.
- `web/src/components/layout/Header.tsx` — unchanged this round (Admin already
  removed; Member Login already present).

## Root causes

1. **Desktop overlap.** `.public-header__inner` used
   `justify-content: space-between` with a **shrinkable** brand
   (`min-width: 0`, default `flex-shrink: 1`) and a nav list with **no
   `min-width: 0`**, so at intermediate widths the brand text overflowed its box
   to the right and the inline links (Home first) ran into the wordmark. The
   inline nav genuinely does not fit inside the ~1104px content area once Home
   was added, so the **900px** mobile breakpoint was too low.
2. **Mobile dead space / odd close button.** The panel is a child of
   `.public-header`, which carries `backdrop-filter: blur(10px)`. A
   `backdrop-filter` (like `filter`/`transform`) makes the element the
   **containing block for `position: fixed` descendants**, so the panel's
   `position: fixed` was resolved against the ~70px header (not the viewport) and
   the `padding-top: calc(76px + 32px)` produced the large void. The only close
   affordance was the header hamburger, visually detached from the panel.

## Fixes

- **Header region structure:** brand is now `flex: 0 0 auto` (never shrinks),
  actions are `flex: 0 0 auto`, and the navigation wrapper owns the flexible
  middle region (`flex: 1 1 auto; min-width: 0; justify-content: center`). The
  nav list is `flex-wrap: nowrap` and compact (`gap: var(--space-4)`,
  `letter-spacing: 0.14em`), so links can never collide with the brand.
- **Deliberate responsive breakpoint:** the hamburger now takes over below
  **1100px** (was 899px), with a tightened inline nav in the
  `1100–1279px` band (`gap: var(--space-3)`, `letter-spacing: 0.08em`). Home
  appears exactly once (only in `Navigation`).
- **Mobile panel geometry:** the header drops `backdrop-filter` at
  `≤1099px` (`backdrop-filter: none`, near-solid bar) to remove the containing
  block; the panel is then anchored with `inset: var(--header-height) 0 0 0`
  and `z-index: calc(var(--z-hud) - 1)` so it sits directly **under** the header
  bar and behind the header's close control. Panel padding reduced from
  `calc(76px + var(--space-6))` to `var(--space-5)`; rows are a consistent 54px
  with hairline separators and full `--color-text` contrast. The header's 46×46
  hamburger (turning into an X) now reads as the panel's top-right close.
- **Panel actions:** Member Login (outlined) + Start a project (primary) grouped
  in `.public-nav__actions`, hidden on desktop (`min-width: 1100px`) to avoid
  duplicating the header actions.
- Body-scroll lock/restore, Escape-to-close, focus trap/restore, ARIA labels and
  `prefers-reduced-motion` were already in place and are preserved.

## Verification

- `npx vitest run public-chrome.test.tsx routing.test.tsx theme-tokens.test.ts
  --no-file-parallelism` — **33 passed** (focused run; full suite not run).
- `npm run typecheck` — clean.
- `npm run build` — succeeds (Vite 7; only the pre-existing chunk-size advisory).

## Needs manual browser inspection

- jsdom does not perform CSS layout, so the overlap fix and the
  `backdrop-filter` containing-block fix were verified by CSS reasoning + the
  build, **not** by rendered pixels. Confirm in a real browser at ~360px,
  ~768px, ~1024px, ~1100px, ~1280px and full desktop, across the six branding
  presets (incl. a custom palette): no brand/nav overlap, panel flush under the
  header with no dead space, and correct stacking over page content.

---

# Mobile Hamburger Position & Menu Refinement

## Root cause of the hamburger sitting too far left

`.public-header__inner` lost its `justify-content` when it was converted to the
three-region layout in the previous fix. On mobile the panel is `position:
fixed` (out of flow) and the `.header-actions` group is hidden and empty, so the
only in-flow children of the header row were the brand and the hamburger. With
`justify-content: flex-start` (the default) both packed to the **left**, leaving
the hamburger floating next to the wordmark instead of at the right edge. (A
secondary contributing factor: the header row is `width: min(1200px, 100%)`
centred — harmless on mobile where it resolves to `100%`, but it means the right
edge is defined by the row's own padding, not by a stray margin.)

## Files and CSS rules changed

- `web/src/styles/public.css`:
  - `.public-header__inner` → restored `justify-content: space-between`.
  - Mobile (`@media max-width: 1099px`): mobile-safe padding
    `max(10px, env(safe-area-inset-top)) max(14px, env(safe-area-inset-right)) …`,
    `.public-brand { margin-right: auto }`, `--header-height: 66px`, and hid
    `.header-cta`/`.header-login` (no actions in the closed mobile bar).
  - `.mobile-menu`: fully opaque `var(--color-background)`, `inset: var(--header-height) 0 0 0`,
    `overflow: hidden`, safe-area bottom/left/right padding, tighter `gap`.
  - `.public-nav__list` / `li` / `a` (mobile): 15px labels, `letter-spacing: 0.03em`,
    `min-height: 46px`, `padding: 8px 4px`, hairline separators.
- `web/src/components/layout/Navigation.tsx` / `Header.tsx`: **unchanged** this
  round (structure already correct; issue was purely CSS layout).

## How the right-edge alignment was established

`space-between` on the header row plus `margin-right: auto` on the brand makes the
brand absorb the free space and push the hamburger flush to the right. Because
the header row is `width: 100%` on mobile with `padding-inline: max(14px,
env(safe-area-inset-right))`, the hamburger's right edge lands **14px** from the
viewport edge (within the requested 12–16px) and the control stays 46px (within
44–48px). No arbitrary margins or absolute positioning were used.

## Menu height and typography

Removed excess whitespace (panel top padding 24px → 12px, row height 54px → 46px,
letter-spacing 0.12em → 0.03em, font 18px → 15px, no internal scrolling). Both
action buttons (Member Login outlined + Start a project primary) remain at the
bottom. Programmatic height check (8 rows + 2 buttons, 66px header):

| Viewport | Available | Menu needs | Slack | Fits |
|----------|-----------|------------|-------|------|
| 390×844  | 778px     | ~531px     | 247px | yes  |
| 430×932  | 866px     | ~531px     | 335px | yes  |
| 360×667  | 601px     | ~531px     | 70px  | yes  |

Every item is visible at once — no scrolling, no hidden links. The overlay is
fully opaque (`--color-background`) and sits below the header within its stacking
context, so homepage text/grid cannot bleed through; body scroll is locked while
open and restored on close; Escape, focus trap/restore, ARIA labels and
`prefers-reduced-motion` are preserved.

## Verification

- `npx vitest run public-chrome.test.tsx --no-file-parallelism` — **7 passed**.
- `npx vitest run routing.test.tsx theme-tokens.test.ts --no-file-parallelism` —
  **26 passed**.
- `npm run typecheck` — clean.
- `npm run build` — succeeds (Vite 7; only the pre-existing chunk-size advisory).
- Programmatic viewport math (table above) confirms the menu fits without scroll.

## Browser visual verification

**Not possible here.** No browser-automation tooling is configured in the repo
(only `jsdom`, which performs no layout), and the environment cannot render
pixels/screenshots. The hamburger's right-edge position, the panel's opacity and
the menu height were therefore validated by CSS reasoning and the programmatic
height calculation above — **not** by visual inspection. Please confirm in a real
browser (or device emulator) at 390×844 and 430×932.

## Remaining uncertainty for manual inspection

- Confirm the hamburger sits ~14px from the right edge with the brand left.
- Confirm the opaque panel fully masks the hero and that no grid/hero text bleeds
  through at the panel edges.
- Confirm all 8 links + 2 action buttons are visible without scrolling (they
  should, with ≥70px slack even on a 360×667 device).
- Confirm the on-screen keyboard / safe-area insets on a notched device do not
  push the bottom action buttons out of view.

---

# Member Work Editor — Card Width & Alignment Fix

## Root cause

On `/member/works/:workId/edit`, the **status/certification `MemberCard`** was a
direct child of `.member-page`, while the Details / Cover image / External links /
Content cards lived inside `<form className="member-stack member-form">`.

- `.member-main` (the content column) is `max-width: 1060px`, so `.member-page`
  spans up to 1060px.
- `.member-form` is capped at `max-width: 860px`.

Because the status card was **outside** the `.member-form` container, it
stretched to the full `.member-page` width (1060px), whereas the form cards were
constrained to 860px. Result: the status/certification card was visibly wider
than the Details card below it and their right edges did not line up. No
`.member-page`, `.member-stack` or `.member-card` rule was missing — the two
groups simply had different width contracts.

## Files changed

- `web/src/pages/member/WorkEditorPage.tsx` — wrapped the status/certification
  `MemberCard` (previously a bare child of `.member-page`) in
  `<div className="member-stack member-form">`, matching the pattern already used
  by `MemberProfilePage` for its non-form summary card.

No CSS was added or changed. No other member page, the sidebar, topbar, header,
colors, typography, APIs, auth or data models were touched.

## Alignment fix

Both the status group and the form now use the identical container contract
(`.member-stack` for vertical rhythm + `.member-form` for the 860px max-width), so
every editor card shares the same left and right boundaries and the same
`--space-6` stack gap. Internal card styling was already correct and is
preserved: `.member-card` padding `--space-5`, `border-radius: var(--radius-lg)`,
`1px solid var(--border)`; `.work-editor__status` is a wrapping flex row;
`.work-cert-panel` is a flex column with a top hairline; `.work-link-row` already
uses `minmax(0, …)` grid columns so inputs cannot overflow.

## Responsiveness

`.member-form`'s `max-width: 860px` has no media-query overrides, so:

- **Desktop (>960px):** both groups are 860px, centred in the 1060px column with
  aligned edges.
- **Tablet (≤960px):** sidebar collapses; `.member-main` narrows; both groups
  fill the available width identically and remain aligned.
- **Mobile (≤620px):** both groups fill the padded content width; the status row
  and link rows wrap; no horizontal overflow.

## Verification

- `npx vitest run src/test/works.test.tsx --no-file-parallelism` — **15 passed**.
- `npm run typecheck` — clean.
- `npm run build` — succeeds (Vite 7; only the pre-existing chunk-size advisory).
- Inspected the actual layout rules (`.member-page`, `.member-main`,
  `.member-stack`, `.member-form`, `.member-card`, `.work-*`) rather than adding
  arbitrary overrides.

## Browser visual verification

**Not possible here.** No browser-automation tooling is configured (only `jsdom`,
which performs no layout) and the environment renders no pixels. The width
equality was verified by reading the layout rules and the container change above,
**not** by screenshot. Please confirm in a real browser that the status,
publication-review, certification and Details cards now share one width with
aligned right edges at desktop, tablet and mobile widths.

---

# Member Work Editor — Vertical Gap Fix

## Root cause

The status/certification card and the Details form are adjacent block siblings in
`.member-page`. The perceived excessive separation was the status card's own
generous internal bottom padding (`.member-card { padding: var(--space-5) }`, 24px
on each side) plus the trailing `.work-cert-panel` spacing, which made the Details
card appear far from the Certification section.

## Change made (CSS only)

`web/src/styles/works.css`:

- `.member-page > .member-stack.member-form > .member-card { padding-bottom: var(--space-3) }`
  — trims the status card's bottom padding (24px → 12px) so the Details card sits
  closer.
- `.member-page > .member-stack.member-form + .member-stack.member-form { margin-top: var(--space-2) }`
  — sets a deliberate 8px gap between the two cards, within the requested
  8–12px range.

Both rules are scoped to the Work Editor's two top-level stacks only. Card widths,
borders, colors, internal padding, typography and all functionality are unchanged.

## Verification

- `npx vitest run src/test/works.test.tsx --no-file-parallelism` — **15 passed**.
- `npm run typecheck` — clean.
- `npm run build` — succeeds.

## Browser visual verification

Not possible here (jsdom has no layout engine). Confirm the gap between the
Certification/status card and the Details card reads as ~8–12px in a real browser.

---

# Contact Page Redesign

## Design changes

Replaced the plain "Get in touch" + grey boxes layout with a deliberate,
art-directed **Editorial Technology Lab + Premium Digital Studio** experience,
built entirely from existing components, tokens and brand patterns.

1. **Hero (`contact-hero`)** — reuses the shared, theme-aware `CosmicField`
   canvas backdrop (same component as the homepage hero) plus the standard
   legibility vignette. Eyebrow `Contact / Start a conversation`, a large
   expressive headline **"Have something worth building?"** (second line as an
   outlined "ghost" line via `-webkit-text-stroke`), the supplied supporting
   text, and a primary **Start a Conversation** action that scrolls to the
   contact section. A restrained **connected-systems SVG diagram** (fine grid,
   node links and a primary-filled hub node) provides the experimental/lab motif
   on the right; it is decorative but carries an accessible `role="img"` label.
2. **Reach the lab (`contact-methods`)** — contact channels rendered as
   equal-height cards in a responsive `auto-fit` grid. Each has a minimal inline
   SVG icon, a clear heading, concise supporting text and the contact detail as
   an interactive link with a hover treatment (border/background lift + arrow
   nudge). Email uses `mailto:`; WhatsApp builds a `https://wa.me/<number>` link
   when the configured value is a phone number (and is rendered as static text
   otherwise); phone uses `tel:`; address is static. Uses only the configured
   contact values — nothing is invented or hardcoded. Social links are preserved
   under an "Elsewhere" sub-block.
3. **Collaboration (`collab-list`)** — a compact editorial list (index number +
   title + concise detail, hairline separators) covering websites/applications,
   business digital presence, product ideas/experiments and collaboration.
4. **Closing (`closing`)** — reuses the homepage `.closing` section:
   **"Every good build starts with a conversation."** with the supplied support
   text and actions linking to the configured email and/or WhatsApp.
5. The old `contact-grid` / `contact-card` styles were replaced with the new
   `contact-*` / `collab-*` rules. Copy was refined to the brand voice; no client
   claims or statistics were added.

## Files changed

- `web/src/pages/public/ContactPage.tsx` — full page redesign.
- `web/src/styles/public.css` — replaced the `contact` block with the new
  art-directed styles (theme-token blended, no literal hex).
- `web/src/test/public-pages.test.tsx` and `web/src/test/routing.test.tsx` —
  updated the contact-page H1 expectation from `/get in touch/i` to the new
  intentional headline `/have something worth building/i`.

No header/footer, other public pages, admin, member portal, APIs, auth, data
models, `.env` or the sibling prototype directory were touched. No new
dependencies.

## Responsive & accessibility checks

- **Desktop:** two-column hero (copy + diagram); contact cards in a multi-column
  `auto-fit` grid.
- **Tablet/mobile (≤900px):** hero collapses to one column with the diagram
  first; contact cards stack; collaboration items remain a single column; no
  horizontal overflow (`min-width: 0` on the grid items and `overflow-wrap:
  anywhere` on long contact strings).
- **Accessibility:** single `h1`, section headings via `aria-labelledby`, the
  diagram labelled with `role="img"` + `aria-label`, inline icons `aria-hidden`,
  links/buttons have clear accessible names, focus states come from the global
  `:focus-visible` rule, and motion respects the global `prefers-reduced-motion`
  block (transitions/animations neutralized).

## Focused verification & build

- `npx vitest run public-pages.test.tsx theme-tokens.test.ts --no-file-parallelism`
  — **21 passed** (theme-tokens asserts `public.css` still contains **zero**
  literal hex colors).
- `npx vitest run routing.test.tsx --no-file-parallelism` — **18 passed**.
- `npx vitest run public-pages public-chrome homepage public-media-seo
  public-members --no-file-parallelism` — **44 passed**.
- `npm run typecheck` — clean. `npm run build` — succeeds.

## Remaining issues requiring browser inspection

- jsdom performs no layout, so the hero composition, diagram scaling, card
  equal-height behaviour and the WhatsApp/email link rendering were verified by
  CSS reasoning + tests, **not** by pixels. Confirm visually at ~360px, ~768px
  and full desktop, and across a light and a dark branding preset (the hero and
  diagram blend from `--color-*`, so both must read correctly).
- Confirm the diagram's `-webkit-text-stroke` ghost line is legible on light
  themes (the stroke blends from `--color-text`, so it should adapt).

---

# Contact Page Artwork Refinement

## What changed

Refined the existing abstract hero visualization (same concept: dark backdrop,
warm amber glow, orbital curves, interconnected nodes) into a **deliberate
orbital composition** — no new dependency, no stock imagery.

**`web/src/pages/public/ContactPage.tsx` (`ContactDiagram`)**

- Removed the arbitrary 6×6 full-bleed grid (`contact-hero__diagram-grid`).
- Replaced the scattered straight polylines with three **concentric orbital
  rings** (rotated ellipses) and five **radial connectors** from a central core
  to nodes placed *on* the rings — a clear hub-and-spoke reading of
  interconnected systems.
- Added an **intelligence core**: a soft layered radial gradient
  (`contact-core`) with a thin ring and a small accent centre dot, plus a
  restrained ambient halo (`contact-halo`).
- Added a subtle `feDropShadow` on the nodes for depth.
- Updated the accessible `role="img"` label to describe the new composition.

**`web/src/styles/public.css` (contact section)**

- Removed `.contact-hero__diagram-grid` rules.
- Orbit rings use faint `--color-text`-blended hairlines (12% / 9%).
- Connectors are faint primary-tinted dotted lines (30%) instead of bright solid
  strokes — clearer hierarchy, less clutter.
- Core/halo gradient stops are styled via CSS classes (`--color-accent` /
  `--color-primary`) so the artwork follows the runtime branding theme.
- Nodes: dark fill with a restrained secondary stroke; the hub node is a solid
  primary fill (4%→ is now deliberate, not full-bright).
- Refined sizing: diagram `width: min(100%, 380px)` with
  `max-height: min(52vh, 380px)` so it never dominates or grows excessively tall;
  mobile (≤900px) caps it to `min(58%, 260px)` / `max-height: min(40vh, 260px)`.
  The hero's `overflow: clip` prevents any clipping/overflow.

The visualization is **static** (no animation added), so `prefers-reduced-motion`
requires no new handling; contact email/WhatsApp remain fully visible and
interactable in the section below.

## Focused verification

- `npx vitest run public-pages.test.tsx theme-tokens.test.ts --no-file-parallelism`
  — **21 passed** (`theme-tokens` confirms `public.css` still has **zero** literal
  hex colors; all artwork colors blend from branding tokens).
- `npm run typecheck` — clean.
- `npm run build` — succeeds.

## Remaining browser inspection

- jsdom has no layout, so the orbital composition, gradient lighting, node depth
  and mobile sizing were verified by CSS reasoning + tests, not pixels. Confirm
  visually at ~360px, ~768px and desktop, on both a light and a dark branding
  preset (the core, halo and connectors all derive from `--color-*`).

---

## Technical SEO optimization

**Goal**: a correct, maintainable SEO foundation across public pages — unique
titles/descriptions, domain-aware canonicals, sitemap/robots, social metadata
and structured data — without ever publishing localhost URLs or leaking private
content.

**Audit findings**

- Backend SEO already existed: `/sitemap.xml` + `/robots.txt`
  (`backend/app/api/routes/seo.py`, URLs from `FRONTEND_URL`, `503` when unset)
  and crawler-readable `/share/*` OG documents + 1200x630 preview images.
- **Gap 1 — localhost canonicals**: `absolutePageUrl` used
  `window.location.origin` unconditionally, so a local dev/preview build emitted
  `http://localhost:5173` as the canonical/OG URL.
- **Gap 2 — robots coverage**: only `/admin` defaulted to `noindex`; `/member`,
  `/setup` and per-ID certificate verification pages were indexable.
- **Gap 3 — sitemap**: the static `/activities` listing was missing.
- **Gap 4 — headings**: `ActivitiesPage` had no `<h1>` (used a section `h2`).

**Changes**

- `web/src/app/config/env.ts`: added `VITE_SITE_URL` (trimmed) as `env.siteUrl`
  / `SITE_URL`.
- `web/src/lib/utils/seo.ts`:
  - `getSiteOrigin()` — prefers `VITE_SITE_URL`; otherwise trusts only a real
    (non-localhost) runtime origin; returns `null` rather than a localhost URL.
  - `absolutePageUrl(path)` — builds canonical/OG URLs from `getSiteOrigin()`,
    returning `null` when no publishable origin exists (tags are then omitted).
  - `defaultRobotsForLocation()` — defaults `noindex, nofollow` for `/admin`,
    `/member`, `/setup`, `/verify-certificate/*` and
    `/verify-activity-certificate/*`.
- `web/src/components/public/SectionHeader.tsx`: optional `level` prop (1|2) so
  a page can render its only heading as `<h1>` while keeping the same markup.
- `web/src/pages/public/ActivitiesPage.tsx`: renders its heading with
  `level={1}` (fixes the missing `<h1>`).
- `backend/app/api/routes/seo.py`: added `/activities` to `_STATIC_PATHS`.
- `web/.env.example`: documented `VITE_SITE_URL`.
- Tests: new `web/src/test/seo.test.ts` (domain-aware canonical + robots
  prefixes: 8 cases); updated `public-media-seo`/`share` assertions to a
  configured test origin (`VITE_SITE_URL=https://thridhalabs.test`, set in
  `vite.config.ts` `test.env`); `test_seo_routes.py` now blanks `FRONTEND_URL`
  at the process level so it overrides the repository `.env` (fixes a
  pre-existing, environment-dependent failure — the real `.env` sets
  `FRONTEND_URL=https://thridhalabs.in`).

**Focused verification**

- `npx vitest run seo public-media-seo share public-pages routing` — **54 passed**.
- `npx vitest run activities homepage maintenance public-chrome public-pages
  routing states careers` — **98 passed**.
- `npm run typecheck` — clean. `npm run build` — succeeds (pre-existing
  chunk-size advisory only).
- `pytest tests/test_seo_routes.py` — **3 passed** (was 2 passed / 1 failed on
  the pre-existing `.env`-dependent test).

**Needs production configuration**

- Set `VITE_SITE_URL` (e.g. `https://thridhalabs.in`) in the production web
  build so canonical/OG URLs are emitted; `FRONTEND_URL` must already be set for
  the backend sitemap/robots. Without `VITE_SITE_URL`, canonical/OG URL tags are
  omitted site-wide rather than pointing at localhost.



