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
