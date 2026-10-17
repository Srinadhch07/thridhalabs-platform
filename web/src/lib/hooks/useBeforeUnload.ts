/**
 * useBeforeUnload — browser-level guard for unsaved changes.
 *
 * Works with any router (the app uses MemoryRouter/BrowserRouter, which do not
 * support data-router `useBlocker`). In-app navigation is guarded separately by
 * each form's discard dialog; this hook covers reload/close and tab-away.
 */

import { useEffect } from 'react'

export function useBeforeUnload(enabled: boolean): void {
  useEffect(() => {
    if (!enabled) return
    function handleBeforeUnload(event: BeforeUnloadEvent): void {
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [enabled])
}