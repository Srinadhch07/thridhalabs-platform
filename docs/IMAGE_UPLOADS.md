# Contextual image uploads (frontend)

Forms that reference a single image — branding logos, client logos, project
thumbnails/galleries, testimonial avatars, work covers and inline work images —
upload that image **in place**. They no longer browse or fetch the global media
library, and they never need a trip to `/admin/media` first.

## Component

`web/src/components/form/ImageUploadField.tsx` exports:

- `ImageUploadField` — one image (value is a `media_id`).
- `ImageGalleryField` — an ordered list of images (value is `media_id[]`).
- Helpers: `validateImageFile`, `imageUploadErrorMessage`, and the constants
  `IMAGE_ACCEPT`, `IMAGE_FORMAT_HINT`, `IMAGE_MAX_BYTES`, `IMAGE_SIZE_HINT`.

Both are controlled fields: they render the current value and call `onChange`
with the new media id(s). The caller owns the form state.

```tsx
import { ImageUploadField } from '../../components/form/ImageUploadField'
import { uploadMedia, resolveAdminMediaPreviewUrl } from '../../features/media/api'

<ImageUploadField
  id="project-thumbnail"
  label="Thumbnail"
  value={form.thumbnail_media_id}
  onChange={(mediaId) => patch({ thumbnail_media_id: mediaId })}
  upload={uploadMedia}                              // admin library
  resolvePreviewUrl={resolveAdminMediaPreviewUrl}   // authenticated preview
  className="admin-section__field"
/>
```

Member-scoped fields use the member uploader and omit `resolvePreviewUrl`
(previews fall back to the public delivery route, which needs no session):

```tsx
import { uploadMemberMedia } from '../../features/media/api'

<ImageUploadField
  id="work-cover"
  label="Cover image"
  value={form.cover_media_id}
  onChange={(mediaId) => patch({ cover_media_id: mediaId })}
  upload={uploadMemberMedia}
/>
```

### Props (both components)

| Prop | Notes |
|------|-------|
| `id`, `label` | `label` labels the hidden file input (accessibility). |
| `value`, `onChange` | Controlled; `string \| null` (single) / `string[]` (gallery). |
| `upload` | `(file) => Promise<Media>` — `uploadMedia` (admin) or `uploadMemberMedia` (member). |
| `resolvePreviewUrl` | Optional `(mediaId) => Promise<string \| null>` for existing references. Omit for member fields. |
| `variant` | Preview variant; defaults to `thumb`. |
| `allowRemove` / `disabled` / `aspectRatio` / `hint` / `className` | Presentation/behaviour. |

## Upload rules

- **Accepted formats**: PNG, JPEG, WebP (enforced in the browser and again by the
  backend from the file's real bytes; the filename/Content-Type are ignored).
- **Size limit**: 5 MB by default (`PRODUCT_IMAGE_MAX_BYTES`). The browser
  pre-checks and the server re-validates; `413 FILE_TOO_LARGE` and
  `415 UNSUPPORTED_MEDIA_TYPE` / `422 INVALID_IMAGE` / `422 IMAGE_TOO_LARGE`
  are mapped to friendly inline messages.
- **Variants**: the backend stores `original`/`thumb`/`md`/`lg` WebP variants.
  Fields preview `thumb` (configurable via `variant`). Display code resolves
  URLs only through `resolveMediaUrl` (`web/src/lib/utils/mediaUrl.ts`).

## Endpoints used

| Context | Upload | Preview of an existing reference |
|---------|--------|----------------------------------|
| Admin forms (branding, clients, projects, testimonials) | `POST /api/media` (`editor`+ , CSRF) | `GET /api/media/{id}` (authenticated) |
| Member works (cover, inline/gallery blocks) | `POST /api/member/media` (CSRF) | `GET /api/public/media/{id}?variant=…` (unauthenticated) |

## Semantics

- **Replace**: the field reference changes only after the new upload succeeds; a
  failed or cancelled upload leaves the previous selection untouched.
- **Remove**: clears the field reference only. The underlying media asset is
  **not** deleted — asset lifecycle stays in the Media library.
- **No library fetch**: opening a form loads at most the single referenced
  thumbnail, never the full media list. The global library remains available to
  admins at `/admin/media` for direct asset management.

## Tests

- `web/src/test/image-upload-field.test.tsx` — component behaviour (empty state,
  upload, preview, replace, remove, client-side validation, disabled,
  accessibility, gallery add/remove).
- `web/src/test/image-upload-pages.test.tsx` — page integration: branding logo
  uploads via `POST /api/media`, member cover via `POST /api/member/media`,
  existing references preview without listing the library.
