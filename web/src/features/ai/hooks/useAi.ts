import { useAsync } from '../../../lib/hooks/useAsync'
import { useCallback, useState } from 'react'
import type { AiSettingsTestResponse } from '../../../types/ai'
import {
  deleteAiSettingsKey,
  generateAiSummary,
  getAiSettings,
  getAiSources,
  getAiSummary,
  listAiSummaries,
  publishAiSummary,
  saveAiSummaryDraft,
  testAiSettings,
  unpublishAiSummary,
  updateAiSettings,
} from '../api/ai'

export function useAiSettings() {
  return useAsync(() => getAiSettings(), [])
}

export function useAiSources() {
  return useAsync(() => getAiSources(), [])
}

export function useAiSummaries(query: {
  page?: number
  page_size?: number
  activity_id?: string
  member_id?: string
  status?: 'draft' | 'published'
} = {}) {
  const key = JSON.stringify(query)
  return useAsync(() => listAiSummaries(query), [key])
}

export function useAiSummary(id: string | undefined) {
  // No summary selected yet is a valid, expected state — resolve to null rather
  // than surfacing a spurious "missing id" error on the page.
  return useAsync(async () => (id ? getAiSummary(id) : null), [id])
}

export function useAiSettingsActions() {
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [removing, setRemoving] = useState(false)
  const [lastTest, setLastTest] = useState<AiSettingsTestResponse | null>(null)
  const [lastError, setLastError] = useState<string | null>(null)

  const test = useCallback(async (apiKey: string) => {
    setTesting(true)
    setLastError(null)
    try {
      const res = await testAiSettings({ api_key: apiKey })
      setLastTest(res)
      return res
    } catch (err: any) {
      setLastError(err?.message || 'Test failed')
      throw err
    } finally {
      setTesting(false)
    }
  }, [])

  const save = useCallback(async (apiKey: string) => {
    setSaving(true)
    setLastError(null)
    try {
      const res = await updateAiSettings({ api_key: apiKey })
      setLastTest(null)
      return res
    } catch (err: any) {
      setLastError(err?.message || 'Save failed')
      throw err
    } finally {
      setSaving(false)
    }
  }, [])

  const remove = useCallback(async () => {
    setRemoving(true)
    setLastError(null)
    try {
      const res = await deleteAiSettingsKey()
      setLastTest(null)
      return res
    } catch (err: any) {
      setLastError(err?.message || 'Remove failed')
      throw err
    } finally {
      setRemoving(false)
    }
  }, [])

  return {
    saving,
    testing,
    removing,
    lastTest,
    lastError,
    test,
    save,
    remove,
    clearError: () => setLastError(null),
    clearTest: () => setLastTest(null),
  }
}

export function useAiSummaryActions(id: string | undefined) {
  const [saving, setSaving] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [unpublishing, setUnpublishing] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const generate = useCallback(
    async (payload: { activity_id: string; member_id: string }) => {
      setGenerating(true)
      setError(null)
      try {
        return await generateAiSummary(payload)
      } catch (err: any) {
        setError(err?.message || 'Generate failed')
        throw err
      } finally {
        setGenerating(false)
      }
    },
    [],
  )

  const saveDraft = useCallback(
    async (draft_content: string) => {
      if (!id) throw new Error('Missing summary id')
      setSaving(true)
      setError(null)
      try {
        return await saveAiSummaryDraft(id, { draft_content })
      } catch (err: any) {
        setError(err?.message || 'Save failed')
        throw err
      } finally {
        setSaving(false)
      }
    },
    [id],
  )

  const publish = useCallback(async () => {
    if (!id) throw new Error('Missing summary id')
    setPublishing(true)
    setError(null)
    try {
      return await publishAiSummary(id)
    } catch (err: any) {
      setError(err?.message || 'Publish failed')
      throw err
    } finally {
      setPublishing(false)
    }
  }, [id])

  const unpublish = useCallback(async () => {
    if (!id) throw new Error('Missing summary id')
    setUnpublishing(true)
    setError(null)
    try {
      return await unpublishAiSummary(id)
    } catch (err: any) {
      setError(err?.message || 'Unpublish failed')
      throw err
    } finally {
      setUnpublishing(false)
    }
  }, [id])

  return {
    saving,
    publishing,
    unpublishing,
    generating,
    error,
    generate,
    saveDraft,
    publish,
    unpublish,
    clearError: () => setError(null),
  }
}
