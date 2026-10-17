"""Dynamic social sharing previews.

Server-rendered, crawler-readable HTML documents plus generated 1200x630
preview images for the three public shareable surfaces:

- Lab Member profiles      `/members/{member_id}`
- Official project pages   `/projects/{slug}`
- Work Showcase pages      `/members/{member_id}/works/{slug}`

The canonical page URLs are served by the React SPA. Because social crawlers do
not execute JavaScript, the reverse proxy routes crawler requests for those
canonical paths to the `/share/...` documents in this module (see
`docs/SOCIAL_SHARING.md`). Everything here respects the exact same public
visibility rules as the public JSON APIs: nothing private, unpublished or
unapproved is ever exposed.
"""
