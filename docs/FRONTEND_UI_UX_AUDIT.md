# FRONTEND_UI_UX_AUDIT.md - Thridha Labs Frontend UI/UX Audit

**Date:** 2026-10-23  
**Repository:** D:\Learning\Projects\thridhalabs  
**Scope:** Investigation-only audit - no code changes made  
**Auditor:** opencode  

---

## 1. Executive Summary

The Thridha Labs frontend is a well-architected React 19 + TypeScript + Vite application with clear separation between public site, admin panel, and member portal. The codebase shows evidence of recent design refinements (Typography update to Times New Roman/Arial, decorative effect reduction, visual weight improvements). 

**Key findings:**
- **Blurred/unclear text:** No evidence of filter:blur(), backdrop-filter causing blur on text directly in most places; blur is used on sticky headers (backdrop-filter) which can create visual blending but not inherently blur text. The largest sources of potential visual clarity issues relate to opacity, transforms on animations, will-change properties, and font rendering.
- **Pulsing dots/animations:** Recent changes have removed most decorative pulsing animations (cosmic field made static, dots made static). A few remain - mostly functional (loaders, skeletons) which are appropriate. The .reveal component uses transform/opacity animations with will-change.
- **Typography:** Headings use Times New Roman (var(--font-heading)), body uses Arial (var(--font-body)) - correctly configured in tokens and globals.css. Consistent across the app.
- **Layout/UX:** Generally well-structured with good responsive patterns. Some potential issues around backdrop-filter creating stacking contexts, animations with will-change, and possible text rendering clarity.

**Top immediate concerns:** Static decorative elements were recently cleaned up, but backdrop-filter on sticky headers and will-change on animations could impact perceived text clarity in some environments.

> **Update (same day):** A headless-Chrome verification pass was completed after this static audit. It confirms several layout/state bugs and identifies the outlined "ghost" headline treatment as a likely cause of the "blurry text" report. See **Section 11** for measured evidence and the revised fix order. The original sections below are retained for traceability.

---

## 2. Brief Frontend Architecture Overview

### Structure
- **Public site:** Routes under PublicLayout (/), Home, Projects, Activities, Clients, Testimonials, About, Contact, Careers, member profiles, work pages, verification pages
- **Admin panel:** /admin/* with AdminLayout (separate route tree, no public chrome)
- **Member portal:** /member/* with MemberAuthProvider and MemberLayout

### Tech Stack
- React 19.2.0, TypeScript, Vite 7.1.9
- react-router-dom 7.9.4
- framer-motion 11.18.2
- CSS with CSS custom properties (design tokens)

### Design System
- **Tokens:** web/src/styles/tokens.css - comprehensive design token system with branding theme support (5 brandable colors that cascade to derived tokens)
- **Global styles:** web/src/styles/globals.css - resets, typography, base components
- **Public styles:** web/src/styles/public.css (54537 bytes) - largest stylesheet for public site
- **Admin/Member styles:** separate stylesheets
- **Fonts:** Times New Roman for headings, Arial for body (configured globally)

### Key Components
- Layout: Header (public), Navigation, Footer, PublicLayout, AdminLayout, MemberLayout
- UI: CosmicField (static canvas backdrop), BackgroundPaths (SVG with framer-motion), Reveal (scroll animations)
- Shared components across routes

---

## 3. Confirmed UI/UX Bugs

### BUG-001: Backdrop-filter on sticky headers may cause text clarity issues
- **Severity:** Medium
- **Confidence:** Probable
- **Affected:** Public header (.public-header at line ~27 in public.css), Admin topbar (line ~40 in admin.css), Member topbar (line ~197 in member.css)
- **Files:**
  - web/src/styles/public.css:27-28 - .public-header { backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); }
  - web/src/styles/admin.css:40 - .admin-topbar { backdrop-filter: blur(8px); }
  - web/src/styles/member.css:197 - .member-topbar { backdrop-filter: blur(10px); }
- **Evidence:** backdrop-filter can create composite layers that affect text rendering clarity, especially on some displays/browsers. Combined with semi-transparent backgrounds.
- **Reproduction:** View sticky header while scrolling; text may appear slightly blurred/fuzzy depending on GPU/compositor.
- **Impact:** Perceived text clarity, especially on lower-end displays
- **Recommended fix:** Test with/without backdrop-filter; consider using semi-transparent background without blur, or ensure proper font-smoothing. Make it configurable or test across browsers.

### BUG-002: will-change on animated elements
- **Severity:** Low
- **Confidence:** Probable  
- **Affected:** .reveal component animations
- **Files:** web/src/styles/public.css:761 - .reveal { will-change: opacity, transform; }
- **Evidence:** will-change: opacity, transform promotes elements to composite layers; while good for performance, can sometimes cause subtle rendering artifacts/text clarity issues in certain scenarios.
- **Impact:** Potential text rendering artifacts on some devices/browsers
- **Recommended fix:** Apply will-change only when animation is active or remove if not necessary. Or use it more sparingly.

### BUG-003: Transform animations on scroll-revealed content
- **Severity:** Low
- **Confidence:** Probable
- **Affected:** Elements using .reveal class
- **Files:** web/src/styles/public.css:757-766, web/src/components/public/Reveal.tsx
- **Evidence:** .reveal { opacity: 0; transform: translateY(18px); transition: opacity 0.7s var(--ease-out), transform 0.7s var(--ease-out); } - transforms can affect text rendering during animation
- **Impact:** Text may appear slightly blurry during scroll animations
- **Recommended fix:** Test; consider using different animation approaches. Respect prefers-reduced-motion (already implemented).
---

## 4. Blurry-Text Investigation

### Investigation Summary
Based on static code analysis, there is **no direct evidence** of `filter: blur()` applied to text elements. The primary sources that can affect perceived text clarity:

### Findings

**BLUR-001: backdrop-filter on sticky/overlay elements (Potential)**
- **Locations:** Public header (10px blur), Admin topbar (8px blur), Member topbar (10px blur), Mobile menu backdrop (2px blur in member.css:769)
- **Type:** Creates backdrop blur behind element, not on text itself
- **Effect:** Can make text appear less crisp due to compositing/blending with blurred background
- **Confidence:** Probable (needs visual verification)
- **Root cause:** CSS backdrop-filter creates a new stacking context and blurs what's behind
- **Note:** The report says "blurred or unclear text" - backdrop-filter is a common culprit for perceived blur even if text isn't directly blurred

**BLUR-002: Animation transforms with will-change**
- **Location:** .reveal uses `transform: translateY()` with `will-change: opacity, transform`
- **Effect:** Transforms can cause text to render on GPU layer, sometimes appearing slightly blurry during/after animation
- **Confidence:** Probable

**BLUR-003: Font rendering and smoothing**
- **Location:** web/src/styles/globals.css:24-26 - -webkit-font-smoothing: antialiased; font-synthesis-weight: none;
- **Status:** Good practice, already applied

**BLUR-004: Opacity on text containers**
- **Findings:** Some elements use reduced opacity (e.g., .reveal starts at opacity:0, but text itself not directly low-opacity in normal state). No obvious opacity < 1 applied directly to text color in normal rendering.
- **Confidence:** Unverified

### Conclusion on "blurred text"
The most plausible causes based on evidence:
1. **backdrop-filter** on sticky headers creating compositing effects (most likely)
2. **GPU layer promotion** from transforms/will-change causing subpixel rendering differences
3. **Font rendering** differences across displays

**Cannot be confirmed without visual/browser testing.** All specific blur sources need inspection in browser dev tools (computed styles, layers panel) while reproducing the issue.

---

## 5. Pulsing Dots and Animation Inventory

### Decorative elements found

**DOT-001: Static dots (recently made static)**
- **.public-brand__dot** (public.css:71-77) - Brand logo dot, now static (no animation) per git history
- **.hud-dot** (public.css:497-503) - Eyebrow dot, static (no animation)
- **Status dots** (globals.css:301-321) - Functional status indicators (.status-dot--ok, .status-dot--pending, .status-dot--err) - **Keep (functional)**

**ANIM-001: Reveal animations (scroll)**
- **Component:** web/src/components/public/Reveal.tsx - IntersectionObserver triggers .reveal.is-in
- **Styles:** opacity + translateY transform, 0.7s duration
- **Purpose:** Scroll-triggered animations - **Borderline decorative/UX**; enhances UX but could be considered motion
- **Respects prefers-reduced-motion:** Yes (globals.css:430-442 disables animations)

**ANIM-002: CosmicField backdrop**
- **Status:** Made static in recent changes (per git diff) - no animation loop, just static render
- **Previous:** Had orbit animations, pulsing core, twinkling - now removed
- **Current:** Static canvas - **Good**

**ANIM-003: BackgroundPaths**
- **Component:** web/src/components/ui/background-paths.tsx
- **Uses framer-motion:** Animates SVG paths with stroke-dasharray animation
- **Respects reduced motion:** Yes (checks useReducedMotion)
- **Purpose:** Decorative background animation
- **Note:** Used on home hero? Let us check usage.

**ANIM-004: Functional animations (keep)**
- **.spinner** (globals.css:337-366) - Loading spinner, rotation animation - **Functional, keep**
- **.skeleton-shimmer** (globals.css:368-387) - Loading skeleton - **Functional, keep**

### Usage of BackgroundPaths
### BackgroundPaths usage
- **Component exists:** web/src/components/ui/background-paths.tsx - SVG animated paths with framer-motion
- **Not currently imported/used** in visible page components (HomePage doesn't import it currently)
- **Tests exist:** background-paths.test.tsx and homepage.test.tsx reference it
- **Status:** Component exists but may not be actively used in current rendered pages; tests suggest it was used previously or is tested

**ANIM-005: Menu animations**
- Mobile menu has transitions (public.css:2070 shows transition-duration adjustments in reduced motion)
- Generally fine

### Summary - Pulsing dots/decorative motion
- Most decorative pulsing animations have been removed (cosmic field made static, brand/hud dots made static per git history)
- **Remaining animations:** Reveal (scroll), BackgroundPaths component (exists but possibly unused), functional loaders/spinners
- **Recommendation:** BackgroundPaths appears unused in current page renders - verify if it's imported anywhere else or can be removed. Reveal adds UX value but is animation; it's properly disabled under prefers-reduced-motion.


---

## 6. Typography, Alignment, and Layout Issues

### Typography Configuration (Confirmed)
- **Headings:** Times New Roman, Times, serif (var(--font-heading)) - set on h1-h6 in globals.css:57
- **Body/General text:** Arial, Helvetica, sans-serif (var(--font-body)) via var(--sans)
- **All form controls:** Inherit font-family (globals.css:34) so they use body font
- **Mono elements:** Use var(--mono) which is now aliased to body font (Arial) per tokens.css:70
- **Status:** Correctly configured as specified

### Typography Issues

**TYPO-001: Mono font aliasing**
- **Files:** web/src/styles/tokens.css:67-70 - --font-heading: "Times New Roman", Times, serif; --font-body: Arial, Helvetica, sans-serif; --sans: var(--font-body); --mono: var(--font-body);
- **Issue:** Both sans and mono aliased to Arial. The comment says "mono are kept as aliases so every existing var() usage follows the body font" - this means code/monospace elements now use Arial instead of a monospace font. That changes the intended design.
- **Impact:** Code blocks, technical labels that might expect monospace will use Arial. May affect readability of technical content.
- **Confidence:** Confirmed (by code)
- **Recommendation:** If monospace is needed for code/technical elements, provide a separate monospace stack.

**TYPO-002: Font loading**
- **Evidence:** No @font-face declarations found, no Google Fonts links in index.html or CSS
- **Status:** Using system fonts only (Times New Roman, Arial) - these are widely available on Windows. Should be fine.
- **Confidence:** Confirmed

### Alignment Issues

**ALIGN-001: Mixed alignment patterns**
- Generally good use of flexbox/grid. No obvious systematic alignment bugs visible in static analysis.
- **Note:** Design uses both centered and left-aligned content depending on section - this appears intentional per editorial design.

**ALIGN-002: Potential text overflow**
- Some elements use max-width constraints (e.g., hero text max-widths) which is good for readability
- Need visual verification for edge cases

### Layout Issues
- Generally solid layout system with CSS Grid/Flexbox
- Responsive breakpoints appear in media queries
- **Need visual verification** for responsive issues across breakpoints

---

## 7. Responsive and Accessibility Issues

### Responsive
- Media queries present in globals.css, public.css, admin.css, member.css
- Mobile menu implementation with focus trap, body scroll lock
- **Verified in browser** at 1440x900, 768x1024, 390x844, 844x390 landscape and 320x568; no horizontal overflow found, but the mobile menu has a layout defect in short viewports (Section 11, V-01).

### Accessibility

**A11Y-001: Focus states**
- **globals.css:46-49:** :focus-visible { outline: 1px solid var(--color-accent); outline-offset: 3px; } - Good
- **Navigation:** Mobile menu traps focus, returns focus on close (Navigation.tsx:102-140) - Good

**A11Y-002: ARIA attributes**
- Mobile menu button has aria-expanded, aria-controls
- CosmicField and decorative elements have aria-hidden="true"
- Good use of semantic HTML

**A11Y-003: Reduced motion**
- **globals.css:430-442:** Disables animations for prefers-reduced-motion
- **Reveal.tsx:** Respects reduced motion
- **BackgroundPaths:** Respects reduced motion
- **CosmicField:** Static (no animations) so fine
- **Good coverage**

**A11Y-004: Skip link**
- **globals.css:106-125:** .skip-link implemented - Good

**A11Y-005: Color contrast**
- Using CSS custom properties with theming system
- Need to verify contrast ratios meet WCAG standards - **Unverified without computed values**

**A11Y-006: Alt text**
- Images have alt attributes in general usage
- **Unverified:** Spot check needed

---

## 8. Relevant Technical and Rendering Issues

### Technical Issues

**TECH-001: backdrop-filter performance**
- backdrop-filter can be expensive on low-end devices
- Multiple elements use it (header, topbars, modals) - could impact performance
- **Confidence:** Probable

**TECH-002: will-change usage**
- .reveal { will-change: opacity, transform; } - promotes to composite layer permanently
- Better to add/remove dynamically or use sparingly
- **Confidence:** Probable

**TECH-003: CSS bundle size**
- public.css is large (54537 bytes) but appears to be well-organized
- No obvious issues

### Rendering Issues
- **Canvas rendering:** CosmicField renders on canvas - generally good, static now
- **Framer-motion:** Used in BackgroundPaths and HomePage animations - adds JS bundle weight
- **No obvious console errors from static analysis**

---

## 9. Prioritized Recommendations

### Priority 1 - Critical/High Impact
1. **Investigate backdrop-filter impact on text clarity** (BUG-001) - Test removing blur from sticky headers, especially public header. This is the most likely cause of perceived blurry text.
2. **Verify font rendering** - Ensure Times New Roman and Arial load correctly across browsers; consider font-display if web fonts were used (currently system fonts only, so fine).

### Priority 2 - Medium Impact  
3. **Review mono font aliasing** (TYPO-001) - If code/technical content needs monospace, restore proper monospace stack. Otherwise document the change.
4. **Optimize will-change usage** (BUG-002) - Only apply will-change during active animations or remove from .reveal base state.

### Priority 3 - Lower Impact / Polish
5. **Check BackgroundPaths usage** - Component exists but may be unused; remove if not needed to reduce bundle size.
6. **Test reduced motion thoroughly** - Ensure all animations respect prefers-reduced-motion (appears good based on code review)
7. **Audit color contrast** - Verify WCAG compliance across themes
8. **Performance testing** - Check backdrop-filter impact on scroll performance
9. **Review transform animations** - Consider alternatives to translateY if causing clarity issues
10. **Cross-browser testing** - Especially for backdrop-filter and font rendering

---

## 10. Verification Limitations and Verified Scope

### Verified
- Project structure, route configuration, design tokens and CSS rules (static analysis).
- Component implementations and the current working-tree changes (git diff).
- Live rendering, computed styles and geometry in headless Chrome at 1440x900, 768x1024, 390x844, 844x390 and 320x568 (Section 11).
- Font availability, horizontal overflow, closed/open mobile menu states, scroll reveals, animation inventory, console exceptions and failed requests on `/`, `/projects`, `/contact`.

### Remaining gaps (not verified)
- **Subjective blur perception** on a physical display/GPU, including DPR > 1. Headless runs used DPR 1; screenshots were captured but not visually interpreted.
- **Data-populated states:** cards, filters, activities, clients, testimonials and member contributions all rendered error states because the API was unavailable.
- **Forms and mutations:** contact submission, admin and member flows were not exercised.
- **Other routes:** Activities, Clients, Testimonials, About, Careers, member/admin layouts and their topbar blurs.
- **Cross-browser/device:** Firefox, Safari, iOS/Android touch behaviour, screen-reader and real keyboard sessions.
- **Performance profiling** of `backdrop-filter` and `will-change`; **contrast across every theme preset**.

### Limitations
- The backend was not running: every `/api/*` request returned HTTP 500, so only error/empty states could be judged.
- Browser automation was performed through the Chrome DevTools Protocol against the Vite dev server, not a production build.
- No app code was changed; this document is the only file modified.

---

## Summary of Key Findings

**Most likely cause of "blurred text":** the deliberately outlined "ghost" headline text (transparent fill + 1.5px stroke at 55% opacity) combined with the desktop header's 82%-opaque, 10px-backdrop-blurred bar, which lets scrolled content ghost through as a blurred smear. See Section 11.

**Pulsing dots/animations:** Most decorative pulsing animations have been removed in recent updates. Remaining animations are mostly functional (loaders) or UX-enhancing (scroll reveals) with proper reduced-motion support.

**Typography:** Correctly configured as specified - Times New Roman for headings, Arial for body text.

**Overall assessment:** The codebase is well-structured with recent design improvements. The main concerns are the outlined "ghost" headline treatment (which reads as blurry), the frosted desktop header, and several concrete responsive/state bugs found in the browser. Full browser verification is documented in Section 11.

---

## 11. Visual Verification Results (Headless Chrome)

**Run date:** 2026-10-23  
**Environment:** Vite dev server at `http://localhost:5173`; headless Chrome 156.0.8078.48 driven over CDP; device pixel ratio 1; viewports 1440x900, 768x1024, 390x844, 844x390 (landscape) and 320x568; pages `/`, `/projects`, `/contact`.  
**Scope:** No application files were modified. Screenshots were captured for human review; the conclusions below come from computed styles, element geometry, DOM text and menu/reveal state, not from machine interpretation of the images.  
**Data caveat:** The backend was not running. Every `/api/*` request returned HTTP 500 (settings, branding, auth, projects, activities, clients, testimonials, contributions). Data-driven sections therefore rendered error states. No JavaScript exceptions were observed.

### 11.1 Newly confirmed issues

#### V-01: Mobile menu content is vertically centered and clips in landscape (High, Confirmed)
- **Cause:** The desktop rule `.mobile-menu { display:flex; justify-content:center }` (public.css:162-167) is never overridden. The mobile block switches to `flex-direction: column` (public.css:296-319) but leaves `justify-content: center`, so the nav + actions group is centered vertically in the fixed panel. The panel also uses `overflow: hidden`.
- **Measured - 390x844:** open panel is 778px tall; first link starts at y=219.6 (a 153px empty gap below the 66px header); actions end at y=685.4. The content fits, but the menu looks top-heavy/empty.
- **Measured - 768x1024:** open panel is 958px tall; first link starts at y=309.6 (243px gap).
- **Measured - 844x390 landscape:** open panel is 324px tall, content scrollHeight is 410px, `overflow` computes to `hidden`. First link renders at y=-7.4 (clipped above the panel) and the actions block spans y=349.6 to 458.4 (below the 390px viewport). The panel cannot scroll, so the top links and both CTAs are unreachable.
- **Fix:** In the mobile block set `justify-content: flex-start` and `overflow-y: auto` (with `min-height: 0`), keep the bottom padding, and verify 844x390 and 320x568.
- **Acceptance:** all seven nav items and both actions reachable with the panel scrolled to the top on a 390px-tall viewport; no content above the panel's top edge.

#### V-02: Hero CTA row is centered on tablet/mobile (Medium, Confirmed)
- **Cause:** `.hero-editorial__cta { justify-content: flex-start }` (public.css:672-674) is declared *before* `.cta-row { justify-content: center }` (public.css:775-781). Both are single-class selectors, so the later rule wins. At desktop the foot's `auto` column shrink-wraps the row, hiding the effect; at <=900px the foot becomes one column and the row centers.
- **Measured:** at 390px the primary CTA is 261.3px wide at x=64.3 (exactly `(390-261.3)/2`), while the H1 and support text start at x=20. At 768px it sits at x=122 (centered in 768), while the H1 starts at x=38.4. The contact/closing CTA is unaffected because `.closing__cta` is declared after `.cta-row`.
- **Fix:** move `.cta-row` above `.hero-editorial__cta`, or use `.hero-editorial .cta-row { justify-content: flex-start }`.
- **Acceptance:** hero CTA left edge matches the support text gutter at 390, 768 and 900px.

#### V-03: Projects error state contradicts itself (Medium, Confirmed)
- **Evidence:** with the API down, `/projects` at 1440 and 390 renders the hero description "INDEXING…" permanently, filter chips read `ALL — 0`, `CLIENT WORK — 0`, etc., while the body shows "Unable to load projects / Request failed with status 500".
- **Cause:** `ProjectsPage.tsx:89` uses `data ? counts : 'Indexing.'`, which treats "no data yet" and "failed to load" identically. `countFor` (ProjectsPage.tsx:78-80) returns 0 for every filter when `entries` is empty.
- **Fix:** branch on `loading` / `error` explicitly, e.g. "Index unavailable" on error; render "—" instead of 0 for counts when no data has loaded; keep the retry action.
- **Acceptance:** error state never says "Indexing", and counts are not presented as real zeroes when loading failed.

#### V-04: Frosted desktop header ghosts scrolled content (Medium, Confirmed mechanism / Probable perception)
- **Evidence:** at 1440 the sticky header computes `background: rgba(7,9,16,0.82)` and `backdrop-filter: blur(10px)` with a 62.2px height (public.css:20-29). The blur is intentionally disabled at <=1099px (public.css:287-291), where the bar is solid and 67px tall.
- **Effect:** when the 122.4px hero headline scrolls under the 62px bar, 18% of it shows through as a 10px-blurred smear behind the brand/nav. Text inside the header stays crisp; the content *behind* it does not. This is a likely part of the "blurry text" report on desktop.
- **Fix:** use an effectively opaque header background, or remove `backdrop-filter` (the blur becomes invisible as opacity approaches 1). This also removes a persistent compositing cost.
- **Acceptance:** scrolling the hero under the header produces no legible/soft ghost band.

#### V-05: Outlined "ghost" text reads as blurry/faint (Medium, Confirmed CSS / Probable perception)
- **Evidence:** Home "can become." and Contact "worth building?" use `color: transparent` plus `-webkit-text-stroke: 1.5px` at 55% opacity (public.css:651-653, 1698-1702; HomePage.tsx:64, ContactPage.tsx:150). The brand "Labs" uses a 1px stroke at 62% (public.css:86-89). The Home H1 computes to 122.4px/117.504px at 1440, 65.28px at 768 and 46px at 390; Contact is 92px and weight 600 (public.css:1689-1697), while other H1/H2s are 700.
- **Effect:** only the glyph edges are painted. At 122.4px a 1.5px stroke is very thin relative to the letterforms, so the phrase reads as hollow and low-ink; users commonly describe this as blurry or out of focus. At 46px the same stroke is proportionally much heavier. Fractional display sizes (122.4px, 65.28px) further reduce edge crispness.
- **Fix:** use a solid fill for the primary headline (the strongest option), or keep the outline only for short decorative words with a thicker/clamp-scaled stroke and higher opacity; snap display sizes to integers (or `round()`), and make the contact hero weight consistent with the rest (700).
- **Acceptance:** the headline's main message is fully filled and passes a "squint test" at 1440 and 390; outlines, if retained, are visibly deliberate rather than faint.

#### V-06: Functional labels lost their monospace face (Low-Medium, Confirmed)
- **Evidence:** `--mono` is aliased to `--font-body` (Arial) in tokens.css:67-70. Measured nav links, eyebrows, filter labels, CTA labels, `ed-head` labels/actions and footer titles all render Arial while still using mono-oriented tracking (0.08em-0.14em) at 12px and 52-66% opacity. The nav is 12px Arial weight 400, "Member Login"/"Start a project" are 12px Arial weight 600.
- **Effect:** proportional Arial with wide/uppercase tracking produces uneven label rhythm and the technical/mono identity is lost. Combined with low-opacity microcopy, metadata can read as soft or poorly spaced.
- **Fix:** restore a true monospace stack for labels (`ui-monospace, SFMono-Regular, Menlo, Consolas, ...`) or retune tracking/weight for Arial; do not keep mono tracking on a proportional face by accident.

#### V-07: Permanent `will-change` on all reveal blocks (Low, Confirmed)
- **Evidence:** `.reveal` keeps `will-change: opacity, transform` (public.css:757-766). At 1440, 11 elements on Home and 11 on Contact compute `will-change: opacity, transform`, including sections already marked `is-in`.
- **Effect:** unnecessary compositor layers remain for the life of the page; not observed to blur text at DPR 1, but wasteful and a possible contributor on GPU-constrained devices.
- **Fix:** apply `will-change` only while the reveal is pending/animating, or remove it (the transition is short and cheap).

#### V-08: Menu focus handling can be improved (Low, Confirmed)
- **Evidence:** opening the menu does not move focus into the panel; the focus trap (Navigation.tsx:63-91) redirects any focus outside the panel to the toggle button and does not wrap from the last item back to the first. Escape close, body scroll lock and focus restoration on close all work.
- **Effect:** keyboard users must tab through the toggle before reaching the first link, and tabbing past the last item jumps back to the toggle rather than cycling. Not a blocker, but a polish/accessibility gap.
- **Fix:** focus the first link (or the panel) on open and implement a true first/last wrap in the trap.

#### V-09: Contact hero weight differs (Low, Confirmed)
- Contact H1 is `font-weight: 600` (public.css:1695) while every other editorial H1/H2 is 700. Together with the outline text this makes the Contact hero look lighter/softer than the Home hero.

### 11.2 Claims not reproduced / ruled out
- **Pulsing dots:** ruled out on the tested public pages. `animCount` was 0 at 1440, 768 and 390 for Home, Projects and Contact. `.public-brand__dot` (7x7) and `.hud-dot` (5x5) compute `animation-name: none`, `box-shadow: none`; `CosmicField` renders once (no animation loop) and its canvas backing store correctly tracks DPR (1440x827 at DPR 1). Only the functional spinner/skeleton animations exist elsewhere in the styles.
- **Horizontal overflow:** none. `scrollWidth == clientWidth == bodyScrollWidth` at 390, 768 and 1440 on all three pages.
- **Font loading:** both `"Times New Roman"` and `Arial` report loaded; body/heading computed families match the tokens.
- **Closed mobile menu:** correctly hidden (`visibility: hidden`, `opacity: 0`, `translateY(-8px)`), not clickable, and does not cover content. The open state is opaque with body scroll locked, so the earlier "panel covers the page" hypothesis is ruled out for the closed state.
- **Reveals:** below-fold `.reveal` elements start at opacity 0 by design; after scrolling to y=1600 all in-view items gained `is-in` (the four still at opacity 0 had y >= 964, below the 900px viewport). No stuck/invisible content found.
- **Runtime health:** no JS exceptions on `/`, `/projects` or `/contact`; all console/network errors were the 500s from the absent backend.

### 11.3 Remaining unverified
- Subjective sharpness on a real monitor/GPU and at DPR 1.25/1.5/2 (headless used DPR 1); screenshots are available but were not interpreted here.
- Data-populated cards/filters/lists and their hover/focus states.
- Contact form submission and other mutations.
- Other public routes (Activities, Clients, Testimonials, About, Careers) and the admin/member layouts.
- Firefox/Safari, touch devices, screen-reader and full keyboard passes, and performance traces.

### 11.4 Revised priority plan

**P0 - fix first (visible layout/brand impact)**
1. **Mobile menu geometry (V-01):** `justify-content: flex-start` + `overflow-y: auto` in the <=1099px block; verify portrait, tablet and 844x390 landscape.
2. **Headline legibility (V-05):** replace the 55%-opacity outlined primary phrases with solid text, or strengthen the stroke and use integer sizes; align Contact weight to 700.
3. **Header ghosting (V-04):** make the desktop header opaque or drop `backdrop-filter`; re-check scroll at 1440.

**P1 - state and alignment correctness**
4. **Hero CTA alignment (V-02):** fix the `.cta-row` cascade at <=900px.
5. **Projects error state (V-03):** loading/error-aware description and counts; no raw "500" copy.
6. **Label typography (V-06):** restore a real mono stack or retune tracking for Arial.

**P2 - performance/polish**
7. **Remove permanent `will-change` (V-07).**
8. **Menu focus wrap + initial focus (V-08).**
9. Re-audit contrast across every branding preset (still open from A11Y-005).

### 11.5 Evidence artifacts
- Screenshots (human review only): `%TEMP%\opencode\shots\evidence-header-scrolled-1440.png`, `evidence-contact-hero-1440.png`, `evidence-hero-390.png`, `evidence-menu-open-390.png`, `evidence-menu-open-landscape-844x390.png`.
- Raw CDP probe output: `%TEMP%\opencode\probe-results.json` (baseline), `probe2-results.json` (menu/hero/reveal), `probe4-results.json` (console/network), `probe5-results.json`, `probe6-results.json` (menu sizing).
