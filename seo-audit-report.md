# SEO Audit Report — Thridha Labs (thridhalabs.in)

Generated: 2025-10-27  
Repository: D:\Learning\Projects\thridhalabs  
Scope: Latest SEO changes (uncommitted + recent diffs). Read-only. No code/config modified.

## 1) Executive summary
- The SEO groundwork aligns with the target domain (env defaults, robots disallows, page metadata updates) and provides value.
- The frontend SEO utility (web/src/lib/utils/seo.ts) is currently broken due to a malformed edit: getSiteOrigin() lost its function declaration/body and is referenced before/without export, isPublicOrigin() remains unused, and there are encoding artifacts. This cascades to getSiteOrigin not exported (tests fail), bsolutePageUrl/shareUrl fail at runtime, and TypeScript fails.
- Backend SEO changes (robots disallows) look correct and low-risk.
- Build/tests are blocked by seo.ts. No live site verified; no GSC actions performed.

## 2) Scope and files investigated
Git diff (name-only, uncommitted): see full list. Key SEO-related:
Frontend: web/index.html, web/src/lib/utils/seo.ts, web/src/test/seo.test.ts, web/src/pages/public/{Home,About,Projects,Activities,Contact,Careers,Clients,Testimonials,Legal,PrivacyPolicy,TermsAndConditions,CookiePolicy}.tsx, web/.env.example, web/vite.config.ts
Backend: backend/app/api/routes/seo.py, backend/app/core/config.py, backend/app/modules/share/metadata.py, .env.example
Env/config: web/src/app/config/env.ts

## 3) Current confirmed errors and root causes
| ID | Sev | File:Line | Error/Observed | Root cause | Blocks | Importance | Rec |
|---|---|---|---|---|---|---|---|
| ERR-001 | Critical | web/src/lib/utils/seo.ts:89-96 | export function getSiteOrigin(): ... { ... } appears after a doc comment but the opening */ was removed in diff; function body is present but declaration is malformed/positioned such that TS cannot resolve references in callers (and export lost in effect). Also earlier diff shows removal of import env and broken restructuring. | Malformed edit during iterative fixes (comment terminated incorrectly, function declaration broken). | tsc, build, tests | Must fix | FIX |
| ERR-002 | Critical | web/src/lib/utils/seo.ts:72-81 | isPublicOrigin defined but TS6133 'isPublicOrigin' declared but never read (current state). | After removing env usage and restructuring, getSiteOrigin no longer calls isPublicOrigin correctly or references are broken; helper left unused. | tsc (warning-as-error not shown, but reported) | Must fix | FIX |
| ERR-003 | Critical | web/src/lib/utils/seo.ts:119,134 and callers | TS2304 Cannot find name 'getSiteOrigin' (absolutePageUrl line ~119, shareUrl ~134). | getSiteOrigin not properly exported/defined in scope due to ERR-001. | tsc, build, runtime | Must fix | FIX |
| ERR-004 | Critical | web/src/test/seo.test.ts:8 | TS2305 Module has no exported member 'getSiteOrigin' | Cascades from ERR-001/ERR-003. | tests, tsc | Must fix | FIX |
| ERR-005 | Medium | web/src/lib/utils/seo.ts (encoding) | Doc comments show â€”, â€” artifacts (UTF-8/encoding). | File encoding/patch artifacts. | Cosmetic/parse noise | Optional | DEFER |
| ERR-006 | Medium | web/src/test/seo.test.ts:22 | ReferenceError window undefined in afterEach when tests fail early | Cascades from export failure. | tests | Optional (fix after exports) | DEFER |

Commands run:
- git diff --name-only (ok)
- git diff --unified=0 web/src/lib/utils/seo.ts (ok)
- git diff --unified=0 backend/app/api/routes/seo.py (ok)
- 
px tsc --noEmit from web/ → errors as above
- 
px vitest run src/test/seo.test.ts → 8 failed, getSiteOrigin not a function

## 4) Frontend findings
| ID | Sev | File | Finding | Evidence | Blocks | Importance | Rec | Notes |
|---|---|---|---|---|---|---|---|---|
| FE-001 | Critical | web/src/lib/utils/seo.ts | Broken getSiteOrigin/export/call chain | Diff shows comment termination broken; getSiteOrigin references env/isPublicOrigin in broken form; tests/imports expect export. | build/tests | Must fix | FIX | Smallest fix: restore proper top-level export using SITE_URL from env.ts and isPublicOrigin; prefer SITE_URL first (matches test expecting SITE_URL). |
| FE-002 | High | web/src/pages/public/HomePage.tsx | Duplicate/errant line introduced (line ~649 shows duplicate description assignment in diff context) | Uncommitted changes show duplicate line. May cause minor issues. | none obvious | Should fix | FIX | Cosmetic/duplication; easy to remove. |
| FE-003 | Medium | web/src/pages/public/LegalPage.tsx | Rewritten to use hooks; syntax issues reported earlier but current file reads cleanly. | Current content valid. Previous errors likely cascaded from seo.ts. | none now | Optional | KEEP | Preserve as-is if compiles after seo.ts fixed. |
| FE-004 | High | web/index.html | Title/description updated to AI-first positioning | Diff shows changes. Good for SEO. | no | Must keep | KEEP | Preserve. |
| FE-005 | Medium | web/src/pages/public/* (About/Projects/Activities/Contact/Careers/Clients/Testimonials) | Title/description updates | Good. | no | Must keep | KEEP | Preserve. |
| FE-006 | Medium | web/.env.example, web/vite.config.ts | VITE_SITE_URL set to https://thridhalabs.in | Good for canonical/origin. | no | Must keep | KEEP | Do not change .env files. |

## 5) Backend findings
| ID | Sev | File | Finding | Evidence | Blocks | Importance | Rec | Notes |
|---|---|---|---|---|---|---|---|---|
| BE-001 | High | backend/app/api/routes/seo.py | Added Disallow for /member/* and verify-certificate/* routes | Diff adds 6 disallow lines in robots generation. Correct to block private/verification routes. | no | Must keep | KEEP | Verify at runtime if desired, but change is correct. |
| BE-002 | Medium | backend/app/core/config.py | FRONTEND_URL default changed to https://thridhalabs.in | Good for canonicals/sharing. | no | Must keep | KEEP | Preserve. |
| BE-003 | Medium | backend/app/modules/share/metadata.py | DEFAULT_DESCRIPTION updated to AI-first | Good. | no | Must keep | KEEP | Preserve. |

## 6) SEO features worth preserving
- Canonical origin preference for https://thridhalabs.in (config/env + logic)
- robots.txt disallows for /admin, /member, /setup, verify-certificate routes
- Per-page metadata updates (titles/descriptions) across public pages
- Legal pages normalized via LegalPage
- Home page Organization/WebSite JSON-LD and metadata
- Share URL helpers (must remain non-null behavior where intended)

## 7) Changes that may be removed or deferred
| Change | Rec | Rationale |
|---|---|---|
| Encoding artifacts (â€”, â€”) | DEFER | Cosmetic; fix after logic. |
| Duplicate description line in HomePage.tsx | FIX/REMOVE small dup | Harmless if last assignment wins, but should clean up. |
| Verbose JSDoc in seo.ts | DEFER | Not blocking. |

## 8) Prioritized fix-vs-remove recommendations
P0 (Critical - blocks build/tests):
1. FIX FE-001: Repair web/src/lib/utils/seo.ts
   - Add import { SITE_URL } from '../../app/config/env'
   - Define isPublicOrigin (or inline) correctly
   - Define export function getSiteOrigin(): string | null as top-level, before use; prefer SITE_URL (from env) first, fallback to window origin if public, else null. Match test expectation (prefers configured production origin = SITE_URL).
   - Ensure all exports remain intact.
2. Verify tests pass after fix.

P1 (High - should fix):
- FE-002: Remove duplicate assignment in HomePage.tsx.

P2 (Optional):
- Clean encoding artifacts if desired.

## 9) Commands run and exact results
- git -C D:\Learning\Projects\thridhalabs diff --name-only → lists modified files (see above)
- git -C D:\Learning\Projects\thridhalabs diff --unified=0 web/src/lib/utils/seo.ts → shows broken edit (comment termination, removed import, added hardcoded origin line)
- git -C D:\Learning\Projects\thridhalabs diff --unified=0 backend/app/api/routes/seo.py → shows added disallows
- Set-Location D:\Learning\Projects\thridhalabs\web; npx tsc --noEmit → 4 errors (seo.ts + seo.test.ts) as reported
- 
px --prefix D:\Learning\Projects\thridhalabs\web vitest run src/test/seo.test.ts → 8/8 failed (getSiteOrigin not a function)

## 10) Unverified areas and remaining uncertainties
- Runtime: sitemap.xml/robots.txt generation not verified via HTTP
- Canonical/OG/JSON-LD correctness across pages not visually verified
- Live site not checked
- GSC not accessed (no submission/indexing)
- Whether SITE_URL is set in test env (test imports SITE_URL from env; vite/vitest config may provide it) — tests expect getSiteOrigin() === SITE_URL

## 11) Proposed remediation order (no implementation performed)
1. Repair seo.ts to restore getSiteOrigin export and fix call chain (use SITE_URL from env.ts). Keep isPublicOrigin if used.
2. Run 
px tsc --noEmit and 
px vitest run src/test/seo.test.ts from web/.
3. Remove duplicate line in HomePage.tsx if present.
4. Quick sanity check of robots/sitemap logic (code review only).
5. Stop — build/tests should pass for SEO scope.

**Confirmation:** No application code or configuration files were modified during this audit. Report written to D:\Learning\Projects\thridhalabs\seo-audit-report.md.
