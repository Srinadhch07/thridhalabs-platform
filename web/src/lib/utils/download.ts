/** Trigger a browser download for an in-memory blob. */

export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  // Revoke on the next tick so the click has started the download.
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
