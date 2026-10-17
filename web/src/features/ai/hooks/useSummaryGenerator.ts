import { useCallback, useEffect, useState } from 'react'
import type { AiSummaryAdminResponse } from '../../../types/ai'
import { useAiSources, useAiSummaryActions } from './useAi'

export function useSummaryGenerator() {
  const { data: sources, loading: sourcesLoading, reload: reloadSources } = useAiSources()
  const { generate, generating, error } = useAiSummaryActions(undefined)
  const [generated, setGenerated] = useState<AiSummaryAdminResponse | null>(null)

  const [activityId, setActivityId] = useState('')
  const [memberId, setMemberId] = useState('')

  const projects = sources?.projects ?? []
  const currentProject = projects.find(p => p.activity_id === activityId)
  const members = currentProject?.members ?? []

  useEffect(() => {
    if (members.length === 0) {
      if (memberId) setMemberId('')
      return
    }
    // Keep the selection valid for the current project: switching projects must
    // not leave a member id from another project (which would post a mismatched
    // pair to the generate endpoint).
    if (!members.some((m) => m.member_id === memberId)) {
      setMemberId(members[0].member_id)
    }
  }, [members, memberId])

  const canGenerate = Boolean(
    activityId &&
      memberId &&
      members.some((m) => m.member_id === memberId) &&
      (currentProject?.approved_count ?? 0) > 0,
  )

  const handleGenerate = useCallback(async () => {
    if (!canGenerate) return
    try {
      const res = await generate({ activity_id: activityId, member_id: memberId })
      setGenerated(res)
      return res
    } catch {
      // The error is already recorded in the actions hook's state.
      return undefined
    }
  }, [activityId, memberId, canGenerate, generate])

  return {
    sources,
    sourcesLoading,
    reloadSources,
    projects,
    currentProject,
    members,
    activityId,
    setActivityId,
    memberId,
    setMemberId,
    canGenerate,
    generating,
    error,
    generated,
    handleGenerate,
  }
}