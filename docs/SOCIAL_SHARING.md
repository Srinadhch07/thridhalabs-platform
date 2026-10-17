# Social Sharing Previews

This document describes the **dynamic social sharing** system: how public pages
get crawlable Open Graph / Twitter Card metadata and generated `1200x630`
preview images, and the **reverse-proxy rule** that connects the canonical SPA
URLs to the backend documents.

- Backend: FastAPI + MongoDB (`backend/app/modules/share/`)
- Frontend: React 19 + TypeScript + Vite (`web/`)
- Preview images: Pillow, rendered on demand (no bundled font files)

---

## 1. Why this exists

The public site is a **pure SPA** (React Router + client-only `usePageMeta`).
The backend is **JSON-only** under `/api` and serves no HTML documents other
than `/sitemap.xml` and `/robots.txt`.

Social crawlers (Facebook, X, LinkedIn, WhatsApp, Slack, Telegram, Discord, …)
**do not execute JavaScript**, so they only ever see the static `index.html`
with its generic `<title>` and no per-page Open Graph tags. To fix that, the
backend renders **server-side HTML documents** for the three shareable public
surfaces, and the reverse proxy routes crawler requests for the canonical URLs
to them.

| Surface                 | Canonical URL (SPA)                          | Backend document |
|-------------------------|----------------------------------------------|------------------|
| Lab Member profile      | `/members/{member_id}`                       | `GET /share/members/{member_id}` |
| Official project page   | `/projects/{slug}`                           | `GET /share/projects/{slug}` |
| Work Showcase detail    | `/members/{member_id}/works/{slug}`          | `GET /share/members/{member_id}/works/{slug}` |

Each document pairs with a generated preview image:

| Image route |
|-------------|
| `GET /share/members/{member_id}/image` |
| `GET /share/projects/{slug}/image` |
| `GET /share/members/{member_id}/works/{slug}/image` |

---

## 2. Metadata contract

Every HTML document carries:

- `<title>` and `<meta name="description">`
- `<link rel="canonical">` and `og:url` = the **canonical SPA URL**
- `og:title`, `og:description`, `og:image`, `og:image:alt`, `og:type`
  (`profile` for members, `article` for works, `website` for projects)
- `og:image:width=1200`, `og:image:height=630`
- `twitter:card=summary_large_image`, `twitter:title`, `twitter:description`,
  `twitter:image`, `twitter:image:alt`

The `og:image` / `twitter:image` URL points at the entity's image route, and the
canonical URL always comes from `FRONTEND_URL` (falling back to the incoming
request's base URL when unset). **Set `FRONTEND_URL` to the public origin in
production** so all advertised URLs are absolute and HTTPS.

### Preview image

- Size `1200x630`, `image/jpeg`.
- Uses the entity's real cover/profile image when available (member profile
  photo, project thumbnail, work cover), cover-cropped with a dark scrim.
- Falls back to a branded canvas when the entity has no image, or when the
  source image cannot be decoded.
- Text is drawn with Pillow's bundled default font
  (`ImageFont.load_default(size=...)`) — **no font file is shipped or loaded from
  disk**, so rendering is identical across platforms.

### Caching

| Response          | `Cache-Control`      |
|-------------------|----------------------|
| HTML `200`        | `public, max-age=300` |
| Image `200`       | `public, max-age=3600` |
| HTML `404`        | `no-store`           |

---

## 3. Visibility & privacy

The share documents reuse the existing public services, so they inherit the
**exact same** visibility rules as the public JSON APIs:

- Member: account `active` **and** profile visibility `public`.
- Project: `published` only.
- Work: `published` **and** work visibility `public` **and** owner active/public.

Any unknown, private, unpublished or unapproved target returns an **identical**
`404` HTML document (`noindex, nofollow`) — the response never reveals whether
the entity exists. Private media and internal assets are never referenced.

Maintenance mode short-circuits with the standard `503 MAINTENANCE_MODE`
response, exactly like the public content APIs.

---

## 4. Reverse-proxy rule

The proxy must send **crawler** requests for the canonical paths to the backend
`/share/...` documents, while **browsers** continue to receive the SPA. The
backend keeps serving the real SPA traffic under its normal `/api`, `/sitemap.xml`
and `/robots.txt` routes.

The following nginx sketch is illustrative — adapt names to your deployment.

```nginx
# 1. Classify social/link-preview crawlers.
map $http_user_agent $social_bot {
    default 0;
    ~*(facebookexternalhit|Facebot|Twitterbot|LinkedInBot|WhatsApp|Slackbot-LinkExpanding|TelegramBot|Discordbot|Pinterest|redditbot|SkypeUriPreview|Googlebot|bingbot|Applebot|Embedly|Quora) 1;
}

server {
    listen 443 ssl;
    server_name thridhalabs.example;

    root /var/www/thridha-labs/web/dist;

    # 2. Work Showcase detail: /members/{id}/works/{slug}
    location ~ ^/members/(?<member>[^/]+)/works/(?<slug>[^/]+)/?$ {
        if ($social_bot) {
            rewrite ^ /share/members/$member/works/$slug last;
        }
        try_files $uri /index.html;
    }

    # 3. Member profile: /members/{id}
    location ~ ^/members/(?<member>[^/]+)/?$ {
        if ($social_bot) {
            rewrite ^ /share/members/$member last;
        }
        try_files $uri /index.html;
    }

    # 4. Project detail: /projects/{slug}
    location ~ ^/projects/(?<slug>[^/]+)/?$ {
        if ($social_bot) {
            rewrite ^ /share/projects/$slug last;
        }
        try_files $uri /index.html;
    }

    # 5. The rewritten /share/... requests are served by the backend.
    location /share/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    }

    # Existing backend mounts.
    location /api/      { proxy_pass http://127.0.0.1:8000; }
    location = /sitemap.xml { proxy_pass http://127.0.0.1:8000; }
    location = /robots.txt  { proxy_pass http://127.0.0.1:8000; }
}
```

Notes:

- The `/share/...` location has **no bot condition** — it is only ever reached
  via the internal rewrites above (or by a crawler that follows the canonical
  `og:image` URL directly), so it is safe to expose.
- `proxy_set_header X-Forwarded-Proto $scheme` matters when `FRONTEND_URL` is
  unset and the base URL is derived from the request.
- The documents deliberately contain **no `meta` refresh** — that would create a
  crawl loop back through the proxy.
- Order the `location` blocks from most specific (`.../works/...`) to least; a
  bare `location ~ ^/members/` would otherwise shadow the work route.

### Alternative: path-prefixed images only

If you prefer not to touch member/project routing, at minimum proxy `/share/`
(the preview images) so the canonical `og:image` URLs resolve. Metadata will
then only be correct for crawlers you route to `/share/...`.

---

## 5. Frontend integration

- `web/src/components/public/ShareActions.tsx` provides native device share,
  "Copy link", and direct targets (X, LinkedIn, Facebook, WhatsApp, Email). It
  **always shares the canonical public URL**, never an admin/internal URL.
- The three public pages (`PublicMemberPage`, `ProjectDetailPage`,
  `PublicWorkPage`) mount `<ShareActions>` and mirror the backend metadata
  client-side: `og:image` / `twitter:image` use the same `/share/.../image` card,
  while JSON-LD `image` keeps the real content image.
- `web/src/lib/utils/seo.ts` exposes `memberShareImagePath`,
  `projectShareImagePath` and `workShareImagePath` plus `ogImageAlt`.

The client-side tags are a best-effort mirror for browser extensions and
client-side navigation; **crawlers get the authoritative tags from the backend
documents**.

---

## 6. Tests

- `backend/tests/test_share_preview.py` — pure unit tests for the HTML renderer
  (required tags, escaping, `noindex` 404) and the preview image
  (size/format, cover crop, corrupt-image fallback).
- `backend/tests/test_share_routes.py` — integration tests: public entities
  return HTML + JPEG; drafts, private profiles and private works return the
  generic `404`.
- `web/src/test/share.test.tsx` — `ShareActions` behavior (copy/native/direct
  targets) and the member page's share controls + preview-image meta.

Run them with:

```
# backend
backend\.venv\Scripts\python.exe -m pytest tests/test_share_preview.py tests/test_share_routes.py -q

# frontend
npx vitest run src/test/share.test.tsx
```

---

## 7. Manual verification

With `FRONTEND_URL` set, a ready backend and a published member/project:

```
curl -i "http://localhost:8000/share/members/THL-M-2026-0001"
curl -i "http://localhost:8000/share/members/THL-M-2026-0001/image"
curl -i "http://localhost:8000/share/members/THL-M-2026-0001/works/<slug>"
curl -i "http://localhost:8000/share/projects/<slug>"
```

A private or unknown id returns `404` with `noindex, nofollow` and no
entity-specific content.
