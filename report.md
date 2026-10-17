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
