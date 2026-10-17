/**
 * Application router.
 *
 * Public application and admin application are clearly separated: the admin
 * namespace lives in its own route tree (no public header/footer, no
 * maintenance gate), so admin routes can never inherit public-only assumptions.
 *
 * Routes:
 *   /, /projects, /projects/:slug, /clients, /testimonials,
 *   /about, /contact, /404, /maintenance-aware public layout
 *   /admin/login (standalone), /admin and its sections (authenticated shell)
 */

import { Outlet, Route, Routes } from 'react-router-dom'
import { AdminLayout } from '../../components/layout/AdminLayout'
import { MemberLayout } from '../../components/layout/MemberLayout'
import { PublicLayout } from '../../components/layout/PublicLayout'
import { MemberAuthProvider } from '../providers/MemberAuthProvider'
import AboutPage from '../../pages/public/AboutPage'
import ActivitiesPage from '../../pages/public/ActivitiesPage'
import ActivityDetailPage from '../../pages/public/ActivityDetailPage'
import CareersPage from '../../pages/public/CareersPage'
import ClientsPage from '../../pages/public/ClientsPage'
import ContactPage from '../../pages/public/ContactPage'
import HomePage from '../../pages/public/HomePage'
import NotFoundPage from '../../pages/public/NotFoundPage'
import ProjectDetailPage from '../../pages/public/ProjectDetailPage'
import ProjectsPage from '../../pages/public/ProjectsPage'
import PublicMemberPage from '../../pages/public/PublicMemberPage'
import PublicWorkPage from '../../pages/public/PublicWorkPage'
import VerifyCertificatePage from '../../pages/public/VerifyCertificatePage'
import TestimonialsPage from '../../pages/public/TestimonialsPage'
import AdminHomePage from '../../pages/admin/AdminHomePage'
import AdminLoginPage from '../../pages/admin/AdminLoginPage'
import AdminSettingsPage from '../../pages/admin/AdminSettingsPage'
import AdminBrandingPage from '../../pages/admin/AdminBrandingPage'
import AdminMediaPage from '../../pages/admin/AdminMediaPage'
import AdminClientsPage from '../../pages/admin/AdminClientsPage'
import AdminClientEditPage from '../../pages/admin/AdminClientEditPage'
import AdminProjectsPage from '../../pages/admin/AdminProjectsPage'
import AdminProjectEditPage from '../../pages/admin/AdminProjectEditPage'
import AdminActivitiesPage from '../../pages/admin/AdminActivitiesPage'
import AdminActivityEditPage from '../../pages/admin/AdminActivityEditPage'
import AdminTestimonialsPage from '../../pages/admin/AdminTestimonialsPage'
import AdminTestimonialEditPage from '../../pages/admin/AdminTestimonialEditPage'
import AdminAccountPage from '../../pages/admin/AdminAccountPage'
import AdminCareersPage from '../../pages/admin/AdminCareersPage'
import AdminCareersOpportunitiesPage from '../../pages/admin/AdminCareersOpportunitiesPage'
import AdminCareerOpportunityEditPage from '../../pages/admin/AdminCareerOpportunityEditPage'
import AdminMembersPage from '../../pages/admin/AdminMembersPage'
import AdminMemberEditPage from '../../pages/admin/AdminMemberEditPage'
import AdminCertificationsPage from '../../pages/admin/AdminCertificationsPage'
import AdminCertificationDetailPage from '../../pages/admin/AdminCertificationDetailPage'
import AdminWorksPage from '../../pages/admin/AdminWorksPage'
import AdminWorkDetailPage from '../../pages/admin/AdminWorkDetailPage'
import AdminReportsPage from '../../pages/admin/AdminReportsPage'
import AdminReportDetailPage from '../../pages/admin/AdminReportDetailPage'
import AdminCertificatesPage from '../../pages/admin/AdminCertificatesPage'
import AdminAiSettingsPage from '../../pages/admin/ai/AdminAiSettingsPage'
import AdminAiSummariesPage from '../../pages/admin/ai/AdminAiSummariesPage'
import AdminNotFoundPage from '../../pages/admin/AdminNotFoundPage'
import MemberLoginPage from '../../pages/member/MemberLoginPage'
import MemberSetupPage from '../../pages/member/MemberSetupPage'
import MemberDashboardPage from '../../pages/member/MemberDashboardPage'
import MemberProfilePage from '../../pages/member/MemberProfilePage'
import MemberAccountPage from '../../pages/member/MemberAccountPage'
import MemberWorksPage from '../../pages/member/MemberWorksPage'
import MemberActivitiesPage from '../../pages/member/MemberActivitiesPage'
import WorkEditorPage from '../../pages/member/WorkEditorPage'
import WorkPreviewPage from '../../pages/member/WorkPreviewPage'
import MemberCertificationsPage from '../../pages/member/MemberCertificationsPage'
import MemberProjectsPage from '../../pages/member/MemberProjectsPage'
import MemberProjectReportsPage from '../../pages/member/MemberProjectReportsPage'
import MemberContributionsPage from '../../pages/member/MemberContributionsPage'

export function AppRouter() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:slug" element={<ProjectDetailPage />} />
        <Route path="/activities" element={<ActivitiesPage />} />
        <Route path="/activities/:slug" element={<ActivityDetailPage />} />
        <Route path="/clients" element={<ClientsPage />} />
        <Route path="/testimonials" element={<TestimonialsPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/contact" element={<ContactPage />} />
        <Route path="/careers" element={<CareersPage />} />
        <Route path="/members/:memberId" element={<PublicMemberPage />} />
        <Route path="/members/:memberId/works/:slug" element={<PublicWorkPage />} />
        <Route path="/verify-certificate/:certificateId" element={<VerifyCertificatePage />} />
        <Route path="/404" element={<NotFoundPage />} />
      </Route>

      <Route path="/admin/login" element={<AdminLoginPage />} />

      <Route path="/admin" element={<AdminLayout />}>
        <Route index element={<AdminHomePage />} />
        <Route path="settings" element={<AdminSettingsPage />} />
        <Route path="branding" element={<AdminBrandingPage />} />
        <Route path="ai/settings" element={<AdminAiSettingsPage />} />
        <Route path="ai/summaries" element={<AdminAiSummariesPage />} />
        <Route path="media" element={<AdminMediaPage />} />
        <Route path="clients" element={<AdminClientsPage />} />
        <Route path="clients/:clientId" element={<AdminClientEditPage />} />
        <Route path="projects" element={<AdminProjectsPage />} />
        <Route path="projects/:projectId" element={<AdminProjectEditPage />} />
        <Route path="activities" element={<AdminActivitiesPage />} />
        <Route path="activities/:activityId" element={<AdminActivityEditPage />} />
        <Route path="testimonials" element={<AdminTestimonialsPage />} />
        <Route path="testimonials/:testimonialId" element={<AdminTestimonialEditPage />} />
        <Route path="careers" element={<AdminCareersPage />} />
        <Route path="careers/opportunities" element={<AdminCareersOpportunitiesPage />} />
        <Route path="careers/opportunities/:opportunityId" element={<AdminCareerOpportunityEditPage />} />
        <Route path="members" element={<AdminMembersPage />} />
        <Route path="members/:memberId" element={<AdminMemberEditPage />} />
        <Route path="works" element={<AdminWorksPage />} />
        <Route path="works/:workId" element={<AdminWorkDetailPage />} />
        <Route path="reports" element={<AdminReportsPage />} />
        <Route path="reports/:reportId" element={<AdminReportDetailPage />} />
        <Route path="certifications" element={<AdminCertificationsPage />} />
        <Route path="certifications/:requestId" element={<AdminCertificationDetailPage />} />
        <Route path="certificates" element={<AdminCertificatesPage />} />
        <Route path="account" element={<AdminAccountPage />} />
        <Route path="*" element={<AdminNotFoundPage />} />
      </Route>

      <Route
        path="/member"
        element={
          <MemberAuthProvider>
            <Outlet />
          </MemberAuthProvider>
        }
      >
        <Route path="login" element={<MemberLoginPage />} />
        <Route path="setup" element={<MemberSetupPage />} />
        <Route element={<MemberLayout />}>
          <Route index element={<MemberDashboardPage />} />
          <Route path="profile" element={<MemberProfilePage />} />
          <Route path="account" element={<MemberAccountPage />} />
          <Route path="works" element={<MemberWorksPage />} />
          <Route path="activities" element={<MemberActivitiesPage />} />
          <Route path="works/new" element={<WorkEditorPage />} />
          <Route path="works/:workId/edit" element={<WorkEditorPage />} />
          <Route path="works/:workId/preview" element={<WorkPreviewPage />} />
          <Route path="certifications" element={<MemberCertificationsPage />} />
          <Route path="projects" element={<MemberProjectsPage />} />
          <Route path="projects/:activityId" element={<MemberProjectReportsPage />} />
          <Route path="contributions" element={<MemberContributionsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

