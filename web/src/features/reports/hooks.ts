/** Reports hooks. */

import { useAsync } from '../../lib/hooks/useAsync'
import type { AdminReportQuery, ReportListQuery } from '../../types/report'
import {
  getAdminReport,
  getContributionHistory,
  getMemberReport,
  listAdminReports,
  listMemberProjects,
  listMemberReports,
} from './api'

export function useMemberProjects() {
  return useAsync(() => listMemberProjects(), [])
}

export function useMemberReports(query: ReportListQuery = {}) {
  return useAsync(() => listMemberReports(query), [JSON.stringify(query)])
}

export function useMemberReport(reportId: string | undefined) {
  return useAsync(async () => {
    if (!reportId) throw new Error('Missing report id')
    return getMemberReport(reportId)
  }, [reportId])
}

export function useContributionHistory() {
  return useAsync(() => getContributionHistory(), [])
}

export function useAdminReports(query: AdminReportQuery = {}) {
  return useAsync(() => listAdminReports(query), [JSON.stringify(query)])
}

export function useAdminReport(reportId: string | undefined) {
  return useAsync(async () => {
    if (!reportId) throw new Error('Missing report id')
    return getAdminReport(reportId)
  }, [reportId])
}
