# SEO_REPORT.md — Thridha Labs (thridhalabs.in)

Generated: 2026-10-27  
Repository: D:\Learning\Projects\thridhalabs  
Scope: Frontend + Backend SEO implementation (as-is). Read-only audit with minimal verification.

## 1) Executive Summary
Thridha Labs has SEO groundwork in place: domain/canonical defaults, robots.txt disallows for private routes, per-page metadata via a reusable SEO utility, legal pages normalized, and homepage Organization/WebSite JSON-LD. Link previews rely on og:image/	witter:image set per page or via defaults; there is currently **no confirmed logo fallback asset** wired as a guaranteed fallback in the codebase. The SEO utility had syntax errors earlier and is currently functional (TypeScript passes, SEO tests pass).

## 2) SEO in Simple English
SEO (Search Engine Optimization) helps search engines understand and show Thridha Labs pages correctly. Link previews (Open Graph/Twitter) control how links look when shared on WhatsApp/LinkedIn/Facebook. Canonical URLs tell search engines the preferred page address. robots.txt/sitemap guide crawling. These help with discoverability/presentation but do **not** guarantee rankings or indexing.

## 3) SEO Features Implemented

| Feature | What it is | What has been done (evidence) | How it helps | Status | Evidence |
|---|---|---|---|---|---|
| Canonical origin | Preferred domain for URLs | getSiteOrigin() prefers env.siteUrl (SITE_URL) else public window origin; bsolutePageUrl() builds canonicals; never emits localhost. | Correct canonicals, avoids duplicate content. | Verified | web/src/lib/utils/seo.ts, web/src/app/config/env.ts, web/src/test/seo.test.ts |
| Per-page metadata | Titles/descriptions/robots | pplyPageMeta()/usePageMeta() manage tags; pages call it. | Better titles/descriptions in browser/search/share. | Implemented but not externally verified | web/src/lib/utils/seo.ts, public pages (Home/About/Projects/Activities/Contact/Careers/Clients/Testimonials/Legal) |
| Open Graph/Twitter | Social previews | pplyPageMeta() sets og:title/description/type/url/image/alt, twitter:card/title/description/image/alt. | Correct previews on supported platforms. | Implemented but not externally verified | web/src/lib/utils/seo.ts |
| Share URLs/images | Share helpers | shareUrl(), siteShareImagePath(), entity share paths; useDefaultOgImage() uses absolute site share image or branding. | Consistent share links/images. | Implemented but not externally verified | web/src/lib/utils/seo.ts |
| Noindex for private routes | Crawl control | defaultRobotsForLocation() noindexes /admin, /member, /setup, /verify-certificate, /verify-activity-certificate prefixes; pplyPageMeta() applies it. | Prevents indexing private/verification pages. | Verified (code/tests) | web/src/lib/utils/seo.ts, web/src/test/seo.test.ts |
| robots.txt (backend) | Crawl directives | Backend adds disallows for /member, /member/*, /verify-certificate/*, /verify-activity-certificate/*. | Reinforces noindexing at server level. | Implemented but not externally verified | ackend/app/api/routes/seo.py |
| Sitemap (backend) | URL list for crawlers | Sitemap generation exists in backend (routes present). Route discovered from implementation. | Helps discovery of public URLs. | Implemented but not externally verified | ackend/app/api/routes/seo.py (and related) |
| Structured data (JSON-LD) | Rich results | HomePage injects WebSite and Organization JSON-LD via useJsonLd(). | May enable rich results. | Implemented but not externally verified | web/src/pages/public/HomePage.tsx |
| Domain config | Prod origin | FRONTEND_URL defaults set to https://thridhalabs.in in backend/config/env examples. | Ensures correct canonicals/origins. | Implemented | ackend/app/core/config.py, .env.example, web/.env.example, web/vite.config.ts |
| Legal pages normalized | Consistent metadata | Legal pages render via LegalPage.tsx with metadata. | Consistent legal SEO/metadata. | Implemented | web/src/pages/public/LegalPage.tsx, legal page files |

## 4) Social Link Preview Report
**Homepage:** HomePage.tsx sets usePageMeta() with title/description/canonical/ogTitle/ogDescription/ogImage (from useDefaultOgImage() or branding) and ogImageAlt. useDefaultOgImage() returns bsolutePageUrl(siteShareImagePath()) ?? brandingOgImage where siteShareImagePath() = /share/site/image.

**Other pages:** Many public pages call usePageMeta() with titles/descriptions/canonicals; some may rely on defaults. Pages without explicit ogImage will use whatever useDefaultOgImage() returns (site share image or branding). If both fail, ogImage may be null/undefined.

**Platforms:** WhatsApp/LinkedIn/Facebook use Open Graph; X uses Twitter cards. The code sets both when image present.

## 5) Logo Fallback Verification
- **Official Thridha Labs logo asset:** Not found in repo search (no *logo* files found in web/public/src). 
- **Fallback logic:** useDefaultOgImage() prefers bsolutePageUrl(siteShareImagePath()) (backend /share/site/image route) else branding OG image. There is **no code path that explicitly falls back to a local logo asset** as a guaranteed last resort. 
- **Status:** **Not implemented / Missing evidence**. If backend /share/site/image is unavailable or returns nothing and branding has no OG image, previews may have no image.
- **Required behavior (stated):** If no page-specific image, use official Thridha Labs logo as fallback (absolute HTTPS on https://thridhalabs.in). This is **not currently satisfied** by codebase evidence.

## 6) Page-by-Page Metadata (key pages)
| Page | Title/Description | Canonical | Preview image behavior |
|---|---|---|---|
| Home (/) | Set via settings + fallbacks; updated to AI-first | bsolutePageUrl('/') | useDefaultOgImage() (site share or branding) |
| About/Projects/Activities/Contact/Careers/Clients/Testimonials | Updated titles/descriptions | Via usePageMeta/helpers where used | Varies; may rely on defaults |
| Legal pages | Normalized via LegalPage | bsolutePageUrl('/' + slug) | Uses useDefaultOgImage() |

## 7) Crawling and Sitemap
- **robots.txt:** Backend generates it with disallows for admin/member/setup/verify routes; frontend applies noindex via meta. Status: Implemented but not externally verified.
- **Sitemap:** Backend has sitemap route; URL not discovered from live check. Status: Implemented but not externally verified.

## 8) Structured Data
- **HomePage:** WebSite + Organization JSON-LD injected. Status: Implemented but not externally verified.

## 9) Tests and Build Results
| Command (from web/) | Result | Notes |
|---|---|---|
| 
px tsc --noEmit | **PASS** | No errors |
| 
px vitest run src/test/seo.test.ts | **PASS** (8/8) | All SEO tests pass |
| 
pm run build | **PASS** | Warnings: CSS syntax warning at minified line ~1165 (source unknown), bundle ~941 kB (>500 kB) |

## 10) What SEO Does Not Guarantee
SEO tags help presentation/discovery but do **not** guarantee search rankings, Google indexing, or immediate refresh of social platform caches (WhatsApp/LinkedIn/Facebook may cache previews).

## 11) Remaining Issues and Recommended Next Steps
- **Critical for previews:** Add a reliable logo fallback. Locate or add an official Thridha Labs logo asset (PNG/WebP/JPG) and ensure useDefaultOgImage() falls back to an absolute HTTPS URL on https://thridhalabs.in when no page-specific/branding/share image exists.
- **Verify externally:** Check /robots.txt, sitemap route, and live page OG tags; test link previews on platforms.
- **Warnings:** Investigate CSS syntax warning source if desired; consider bundle splitting.
- **Full tests:** Unrelated failures exist in full suite (not blocking SEO/build).

## 12) Evidence and File References
- web/src/lib/utils/seo.ts - SEO helpers/hooks
- web/src/app/config/env.ts - SITE_URL/env
- web/src/pages/public/HomePage.tsx - metadata + JSON-LD
- web/src/pages/public/LegalPage.tsx - legal metadata
- web/index.html - base meta/title
- ackend/app/api/routes/seo.py - robots/sitemap
- ackend/app/core/config.py - FRONTEND_URL default
- web/src/test/seo.test.ts - SEO tests

**Logo fallback:** Not implemented. No logo asset found. Recommend adding logo asset and updating useDefaultOgImage() to use absolute logo URL as final fallback.
# SEO_REPORT.md — Thridha Labs (thridhalabs.in) — Updated

Generated: 2026-10-27  
Repository: D:\Learning\Projects\thridhalabs  

## Executive Summary
SEO groundwork is in place. The admin-uploaded logo is now used as the final fallback for Open Graph/Twitter previews when no page-specific or branding OG image is configured.

## Logo Source (Admin Upload)
- **Where uploaded:** Admin → Branding (/admin/branding) via AdminBrandingPage.tsx. Media fields include logo, logo_dark, logo_light, avicon, og_image (stored as media IDs).
- **Storage:** Backend randing module stores media references; media validated via equire_media_exist. Files stored via existing media service (local/S3 depending on config) — not changed.
- **API:** Public GET /api/public/branding returns branding (no auth). Admin endpoints exist. Frontend uses getPublicBranding() via BrandingProvider.
- **Frontend retrieval:** useBranding() provides data.media.logo/logo_light/logo_dark. Resolved via esolveMediaUrl(id, 'md') through public media delivery (/api/public/media/{id}?variant=...).
- **Public accessibility:** Public branding endpoint is unauthenticated; media resolved via public media route when using media ID strings — publicly accessible if served by backend.

## Image Fallback Priority (Updated)
1. Page-specific ogImage/	witter:image (explicit in usePageMeta/pplyPageMeta)
2. Site share image from backend: bsolutePageUrl(siteShareImagePath()) (/share/site/image)
3. Branding OG image: useBrandingOgImage() from data.media.og_image
4. **Admin-uploaded logo (final fallback):** useBrandingLogoImage() from data.media.logo ?? data.media.logo_light ?? data.media.logo_dark (resolved via esolveMediaUrl)

If backend returns relative URLs, they are resolved by esolveMediaUrl/bsolutize using API origin; bsolutePageUrl ensures canonical-origin absolute URLs where applicable. Production metadata avoids localhost when possible.

## Changes Made
- web/src/lib/utils/seo.ts: Added useBrandingLogoImage() and updated useDefaultOgImage() to use logo as final fallback.
- web/src/test/seo.test.ts: Added test for page-specific image priority.

## Tests and Build
| Command (web/) | Result |
|---|---|
| 
px tsc --noEmit | PASS |
| 
px vitest run src/test/seo.test.ts | PASS (9/9) |
| 
pm run build | PASS (warnings: CSS syntax at minified line ~1165 source unknown; bundle ~941 kB) |

## Verification Notes
- Code-level verification only. Social platforms may cache previews; client-side metadata updates may not guarantee crawler reads depending on rendering. Public endpoints not probed in this run.
- No duplicate logo upload system added. Existing admin flow reused.
- Page-specific images unchanged. No localhost URLs introduced by fallback logic.

## Remaining Issues
- CSS syntax warning source unknown; bundle size large (performance only).
- External platform preview verification not performed.
- Full test suite has unrelated failures.
