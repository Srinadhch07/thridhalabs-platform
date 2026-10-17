/** Reports feature API — member progress reports + admin review queue. */

import { api } from '../../lib/api/client'
import type { QueryParams } from '../../lib/api/client'
import type { Paginated } from '../../types/pagination'
import type {
  AdminReport,
  AdminReportQuery,
  ContributionHistory,
  MemberProjectList,
  MemberReport,
  ReportCreatePayload,
  ReportDecisionPayload,
  ReportListQuery,
  ReportUpdatePayload,
} from '../../types/report'

// --- Member -----------------------------------------------------------------

export function listMemberReports(
  query: ReportListQuery = {},
): Promise<Paginated<MemberReport>> {
  return api.get<Paginated<MemberReport>>('/member/reports', { query: query as QueryParams })
}

export function listMemberProjects(): Promise<MemberProjectList> {
  return api.get<MemberProjectList>('/member/reports/projects')
}

export function getContributionHistory(): Promise<ContributionHistory> {
  return api.get<ContributionHistory>('/member/reports/contributions')
}

export function getMemberReport(reportId: string): Promise<MemberReport> {
  return api.get<MemberReport>(`/member/reports/${reportId}`)
}

export function createMemberReport(payload: ReportCreatePayload): Promise<MemberReport> {
  return api.post<MemberReport>('/member/reports', payload)
}

export function updateMemberReport(
  reportId: string,
  payload: ReportUpdatePayload,
): Promise<MemberReport> {
  return api.patch<MemberReport>(`/member/reports/${reportId}`, payload)
}

// --- Admin ------------------------------------------------------------------

export function listAdminReports(
  query: AdminReportQuery = {},
): Promise<Paginated<AdminReport>> {
  return api.get<Paginated<AdminReport>>('/admin/reports', { query: query as QueryParams })
}

export function getAdminReport(reportId: string): Promise<AdminReport> {
  return api.get<AdminReport>(`/admin/reports/${reportId}`)
}

export function decideAdminReport(
  reportId: string,
  payload: ReportDecisionPayload,
): Promise<AdminReport> {
  return api.post<AdminReport>(`/admin/reports/${reportId}/decision`, payload)
}
