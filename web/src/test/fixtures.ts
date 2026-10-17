/** Shared fixtures representing the backend API contracts. */

import type { PublicBranding, AdminBranding } from '../types/branding'
import type {
  AdminCareersSettings,
  AdminOpportunity,
  PublicCareersSettings,
  PublicOpportunity,
} from '../types/careers'
import type { PublicProject, PublicClient, PublicTestimonial, AdminClient, AdminProject, AdminTestimonial } from '../types/content'
import type { Paginated } from '../types/pagination'
import type { PublicSiteSettings, AdminSiteSettings } from '../types/settings'
import type { Media } from '../types/media'
import type { Me } from '../types/admin'
import type {
  MemberAdmin,
  MemberMe,
  MemberProfileInfo,
  MemberProfileResponse,
  PublicContributionSummary,
  PublicMemberProfile,
} from '../types/member'
import type {
  ContentDocument,
  MemberWork,
  WorkCard,
  WorkCertificationRef,
  WorkPublic,
  WorkPublicCard,
} from '../types/work'
import type { CertificationCard, CertificationDetail } from '../types/certification'
import type {
  CertificateAdmin,
  CertificateMember,
  PublicCertificate,
  PublicCertificateWork,
} from '../types/certificate'
import type {
  AdminActivity,
  MemberActivity,
  PublicActivity,
  ActivityParticipant,
} from '../types/activity'
import type {
  AdminReport,
  ContributionHistory,
  MemberProjectSummary,
  MemberReport,
} from '../types/report'
import type {
  AiSourceOverviewResponse,
  AiSummaryAdminResponse,
  AiSummaryListResponse,
} from '../types/ai'

export const settingsFixture: PublicSiteSettings = {
  general: {
    site_name: 'Thridha Labs',
    tagline: 'We experiment with intelligence.',
    description: 'AI, software and ideas turned into things people can actually use.',
  },
  contact: {
    contact_email: 'hello@thridhalabs.com',
    contact_phone: null,
    whatsapp: null,
    address: null,
  },
  social: { urls: {} },
  footer: { copyright_text: '© 2026 Thridha Labs' },
  seo: { seo_title: 'Thridha Labs', seo_description: 'A technology and AI experimentation lab.', seo_keywords: [] },
  maintenance_mode: false,
}

export const brandingFixture: PublicBranding = {
  colors: {
    primary: '#4f46e5',
    secondary: '#0ea5e9',
    accent: '#f59e0b',
    background: '#ffffff',
    text: '#0f172a',
  },
  mode: 'light',
  media: { logo: null, logo_dark: null, logo_light: null, favicon: null, og_image: null },
}

export const careersSettingsFixture: PublicCareersSettings = {
  enabled: false,
  heading: null,
  description: null,
  application_template: null,
}

export const enabledCareersSettingsFixture: PublicCareersSettings = {
  enabled: true,
  heading: 'Open roles at the lab',
  description: 'Ways to work with the lab.',
  application_template: 'Tell us about yourself and what you would like to build.',
}

export const emptyList = <T,>(): Paginated<T> => ({
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
  pages: 0,
})

export const meFixture: Me = {
  id: 'admin-1',
  email: 'owner@thridhalabs.com',
  role: 'owner',
  is_active: true,
}

function paginated<T>(items: T[]): Paginated<T> {
  return { items, total: items.length, page: 1, page_size: 20, pages: items.length > 0 ? 1 : 0 }
}

export const adminSettingsFixture: AdminSiteSettings = {
  ...settingsFixture,
  id: 'settings-1',
  analytics: { google_verification: null, google_analytics: null },
  maintenance_mode: false,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

export const adminBrandingFixture: AdminBranding = {
  ...brandingFixture,
  id: 'branding-1',
  theme_preset: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

export const adminCareersSettingsFixture: AdminCareersSettings = {
  ...enabledCareersSettingsFixture,
  id: 'careers-1',
  application_email: 'apply@thridhalabs.com',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

export const publicOpportunityFixture: PublicOpportunity = {
  slug: 'lab-member',
  title: 'Lab Member',
  type: 'lab-member',
  custom_type: null,
  description: 'Build things alongside the lab.',
  skills: ['Python', 'LLMs'],
  work_mode: 'remote',
  application_email: 'apply@thridhalabs.com',
}

export const adminOpportunityFixture: AdminOpportunity = {
  ...publicOpportunityFixture,
  id: 'opp-1',
  status: 'open',
  display_order: 0,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

export const adminClientFixture: AdminClient = {
  id: 'c-1',
  slug: 'acme',
  name: 'Acme Co',
  logo_media_id: null,
  featured_image_media_id: null,
  description: '',
  website: null,
  industry: 'Energy',
  category: null,
  featured: true,
  display_order: 0,
  project_ids: [],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

export const adminProjectFixture: AdminProject = {
  id: 'p-1',
  slug: 'atlas-engine',
  name: 'Atlas Engine',
  thumbnail_media_id: null,
  gallery_media_ids: [],
  description: 'An experimental AI reasoning engine.',
  category: 'AI',
  technologies: ['Python', 'LLMs'],
  live_url: null,
  github_url: null,
  project_type: 'experiment',
  featured: true,
  display_order: 0,
  completion_date: null,
  client_id: null,
  client: null,
  status: 'published',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

export const adminTestimonialFixture: AdminTestimonial = {
  id: 't-1',
  client_id: null,
  client: null,
  person_name: 'Ada Lovelace',
  role: 'Partner',
  testimonial_text: 'A remarkable team that ships.',
  profile_image_media_id: null,
  company: 'Acme Co',
  rating: 5,
  featured: true,
  published: true,
  status: 'approved',
  display_order: 0,
  date: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

export const pendingTestimonialFixture: AdminTestimonial = {
  ...adminTestimonialFixture,
  id: 't-pending',
  person_name: 'Pat Visitor',
  published: false,
  featured: false,
  status: 'pending',
}

export const mediaFixture: Media = {
  id: 'm-1',
  original_name: 'hero.webp',
  format: 'webp',
  mime_type: 'image/webp',
  media_type: 'image',
  size_bytes: 20480,
  width: 800,
  height: 600,
  checksum: 'abcdef0123456789deadbeef',
  storage_mode: 'local',
  variants: [
    { name: 'original', object_key: 'media/m-1/original.webp', width: 800, height: 600, size_bytes: 20480, mime_type: 'image/webp' },
    { name: 'thumb', object_key: 'media/m-1/thumb.webp', width: 128, height: 96, size_bytes: 2048, mime_type: 'image/webp' },
  ],
  urls: {
    original: '/api/media/m-1/file?variant=original',
    thumb: '/api/media/m-1/file?variant=thumb',
  },
  created_by: 'admin-1',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

export const adminClientsFixture = (): Paginated<AdminClient> => paginated([adminClientFixture])
export const adminProjectsFixture = (): Paginated<AdminProject> => paginated([adminProjectFixture])
export const adminTestimonialsFixture = (): Paginated<AdminTestimonial> => paginated([adminTestimonialFixture])
export const mediaFixtureList = (): Paginated<Media> => paginated([mediaFixture])

/** A wide banner image with a large variant (used by activity banner preview). */
export const bannerMediaFixture: Media = {
  ...mediaFixture,
  id: 'banner-1',
  original_name: 'banner.webp',
  width: 1920,
  height: 1080,
  variants: [
    { name: 'original', object_key: 'media/banner-1/original.webp', width: 1920, height: 1080, size_bytes: 90000, mime_type: 'image/webp' },
    { name: 'lg', object_key: 'media/banner-1/lg.webp', width: 1920, height: 1080, size_bytes: 60000, mime_type: 'image/webp' },
  ],
  urls: {
    original: '/api/media/banner-1/file?variant=original',
    lg: '/api/media/banner-1/file?variant=lg',
  },
}
export const adminOpportunitiesFixture = (): Paginated<AdminOpportunity> => paginated([adminOpportunityFixture])

export const adminDataHandlers = () => ({
  '/api/auth/me': { body: meFixture },
  '/api/auth/csrf': { body: { csrfToken: 'test-csrf' } },
  '/api/auth/logout': { body: { status: 'ok' } },
  '/api/clients': { body: adminClientsFixture() },
  '/api/clients/c-1': { body: adminClientFixture },
  '/api/projects': { body: adminProjectsFixture() },
  '/api/projects/p-1': { body: adminProjectFixture },
  '/api/testimonials': { body: adminTestimonialsFixture() },
  '/api/testimonials/t-1': { body: adminTestimonialFixture },
  '/api/careers': { body: adminCareersSettingsFixture },
  '/api/careers/opportunities': { body: adminOpportunitiesFixture() },
  '/api/careers/opportunities/opp-1': { body: adminOpportunityFixture },
  '/api/members': { body: adminMembersFixture() },
  '/api/members/member-1': { body: adminMemberFixture },
  '/api/media': { body: mediaFixtureList() },
  '/api/media/m-1': { body: mediaFixture },
  '/api/settings': { body: adminSettingsFixture },
  '/api/branding': { body: adminBrandingFixture },
})

export const editorMeFixture: Me = {
  id: 'admin-2',
  email: 'editor@thridhalabs.com',
  role: 'editor',
  is_active: true,
}

export const projectsFixture = (): Paginated<PublicProject> => ({
  items: [
    {
      slug: 'atlas-engine',
      name: 'Atlas Engine',
      thumbnail_media_id: null,
      gallery_media_ids: [],
      description: 'An experimental AI reasoning engine.',
      client: null,
      category: 'AI',
      technologies: ['Python', 'LLMs'],
      live_url: null,
      github_url: 'https://github.com/example/atlas',
      project_type: 'experiment',
      featured: true,
      display_order: 0,
      completion_date: null,
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
  pages: 1,
})

export const projectDetailsFixture: PublicProject = projectsFixture().items[0]

export const clientsFixture = (): Paginated<PublicClient> => ({
  items: [
    {
      slug: 'acme',
      name: 'Acme Co',
      logo_media_id: null,
      featured_image_media_id: null,
      description: '',
      website: null,
      industry: 'Energy',
      category: null,
      featured: true,
      display_order: 0,
      projects: [],
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
  pages: 1,
})

export const testimonialsFixture = (): Paginated<PublicTestimonial> => ({
  items: [
    {
      id: 't-1',
      person_name: 'Ada Lovelace',
      role: 'Partner',
      testimonial_text: 'A remarkable team that ships.',
      profile_image_media_id: null,
      company: 'Acme Co',
      rating: 5,
      featured: true,
      display_order: 0,
      date: null,
      client: null,
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
  pages: 1,
})

export const opportunitiesFixture = (): Paginated<PublicOpportunity> => paginated([publicOpportunityFixture])

// --- Members ---------------------------------------------------------------

export const memberProfileFixture: MemberProfileInfo = {
  display_name: 'Ada',
  bio: 'Lab member working on embodied AI.',
  skills: ['Python', 'Robotics'],
  interests: ['Sustainability', 'Open hardware'],
  github_url: null,
  linkedin_url: null,
  portfolio_url: null,
  location: 'Bengaluru, India',
  timezone: 'Asia/Kolkata',
  picture_media_id: null,
  profile_visibility: 'public',
  completed_at: '2026-01-02T00:00:00Z',
}

export const memberMeFixture: MemberMe = {
  id: 'member-1',
  member_id: 'THL-M-2026-0001',
  email: 'member@thridhalabs.com',
  status: 'active',
  full_name: 'Ada Lovelace',
  profile_complete: true,
  last_login_at: '2026-02-01T10:00:00Z',
}

export const memberProfileResponseFixture: MemberProfileResponse = {
  id: memberMeFixture.id,
  member_id: memberMeFixture.member_id,
  email: memberMeFixture.email,
  status: memberMeFixture.status,
  full_name: memberMeFixture.full_name,
  role_label: 'Research Member',
  profile: memberProfileFixture,
  profile_complete: true,
  created_at: '2026-01-01T00:00:00Z',
}

export const adminMemberFixture: MemberAdmin = {
  id: memberMeFixture.id,
  member_id: memberMeFixture.member_id,
  email: memberMeFixture.email,
  status: memberMeFixture.status,
  full_name: memberMeFixture.full_name,
  role_label: 'Research Member',
  joined_opportunity_id: null,
  internal_note: null,
  profile: memberProfileFixture,
  profile_complete: true,
  onboarding_sent: true,
  onboarding_completed_at: '2026-01-02T00:00:00Z',
  created_by: 'admin-1',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
  last_login_at: memberMeFixture.last_login_at,
}

export const adminMembersFixture = (): Paginated<MemberAdmin> => paginated([adminMemberFixture])

/** Build an admin member view from the base fixture. */
export const adminMemberWith = (overrides: Partial<MemberAdmin> = {}): MemberAdmin => ({
  ...adminMemberFixture,
  ...overrides,
})

/**
 * A pool of members for the invitation member-selection tests: 12 active
 * members (one of whom — `member-1` — is already a confirmed participant) plus
 * one inactive and one pending-setup member.
 */
export const inviteMembersPool = (): MemberAdmin[] => {
  const roles = ['AI Engineer', 'Frontend Developer', 'Backend Developer', 'Product Analyst']
  const members: MemberAdmin[] = [adminMemberWith()]
  for (let i = 2; i <= 12; i += 1) {
    members.push(
      adminMemberWith({
        id: `member-${i}`,
        member_id: `THL-M-2026-${String(i).padStart(4, '0')}`,
        email: `member${i}@thridhalabs.com`,
        full_name: `Member ${i}`,
        role_label: roles[i % roles.length],
        status: 'active',
      }),
    )
  }
  members[1] = adminMemberWith({
    ...members[1],
    full_name: 'Grace Hopper',
    email: 'grace@thridhalabs.com',
    role_label: 'Frontend Developer',
  })
  members[2] = adminMemberWith({
    ...members[2],
    full_name: 'Alan Turing',
    email: 'alan@thridhalabs.com',
    role_label: 'Backend Developer',
  })
  members[3] = adminMemberWith({
    ...members[3],
    full_name: 'Katherine Johnson',
    email: 'katherine@thridhalabs.com',
    role_label: 'Product Analyst',
  })
  members[4] = adminMemberWith({
    ...members[4],
    full_name: 'Ivan Inactive',
    email: 'inactive@thridhalabs.com',
    status: 'inactive',
  })
  members[5] = adminMemberWith({
    ...members[5],
    full_name: 'Penny Pending',
    email: 'pending@thridhalabs.com',
    status: 'pending_setup',
  })
  return members
}

// --- Works ------------------------------------------------------------------

export const workContentFixture: ContentDocument = {
  version: 1,
  blocks: [
    { type: 'heading', level: 2, text: 'Overview' },
    { type: 'paragraph', spans: [{ text: 'An embodied AI experiment.' }] },
    {
      type: 'external_link',
      label: 'Repository',
      url: 'https://github.com/example/embodied',
    },
  ],
}

export const workCertificationRefFixture: WorkCertificationRef = {
  request_id: null,
  status: null,
  version_reviewed: null,
  reviewed_at: null,
  feedback: null,
  changed_since_review: false,
  reviewable: false,
}

export const workCardFixture: WorkCard = {
  id: 'w-1',
  member_id: memberMeFixture.id,
  title: 'Embodied Agents',
  slug: 'embodied-agents',
  summary: 'A study of embodied AI agents.',
  cover_media_id: null,
  tags: ['Robotics', 'AI'],
  visibility: 'public',
  publication_status: 'published',
  version: 2,
  certification: workCertificationRefFixture,
  submitted_at: '2026-01-15T00:00:00Z',
  review_feedback: null,
  reviewed_at: '2026-01-18T00:00:00Z',
  featured_on_projects: false,
  featured_classification: null,
  created_at: '2026-01-10T00:00:00Z',
  updated_at: '2026-02-01T00:00:00Z',
  published_at: '2026-01-20T00:00:00Z',
}

export const memberWorkFixture: MemberWork = {
  ...workCardFixture,
  external_links: [{ label: 'Repository', url: 'https://github.com/example/embodied' }],
  content: workContentFixture,
  profile_visibility: 'public',
  featured_at: null,
}

export const workListFixture = (items: WorkCard[] = [workCardFixture]): Paginated<WorkCard> =>
  paginated(items)

export const publicWorkCardFixture: WorkPublicCard = {
  slug: workCardFixture.slug,
  title: workCardFixture.title,
  summary: workCardFixture.summary,
  cover_media_id: null,
  tags: workCardFixture.tags,
  published_at: workCardFixture.published_at as string,
}

export const publicWorkCardFixture2: WorkPublicCard = {
  slug: 'neural-echoes',
  title: 'Neural Echoes',
  summary: 'An audio-reactive generative installation.',
  cover_media_id: 'media-cover-2',
  tags: ['Creative Coding', 'Audio'],
  published_at: '2026-02-10T00:00:00Z',
}

export const publicContributionFixture: PublicContributionSummary = {
  activity_title: 'Automotive Accessories Digital Platform',
  role: 'Backend Developer',
  content: 'Worked on the backend project setup, employing FastAPI, MongoDB and Redis.',
  published_at: '2026-10-16T17:42:21.552000',
  source_report_count: 1,
  period_start: '2026-10-01T00:00:00Z',
  period_end: '2026-10-15T00:00:00Z',
}

export const publicMemberFixture: PublicMemberProfile = {
  member_id: memberMeFixture.member_id,
  display_name: 'Ada Lovelace',
  bio: memberProfileFixture.bio,
  skills: memberProfileFixture.skills,
  interests: memberProfileFixture.interests,
  github_url: null,
  linkedin_url: null,
  portfolio_url: null,
  location: memberProfileFixture.location,
  picture_media_id: null,
  works: [publicWorkCardFixture],
  contributions: [publicContributionFixture],
}

export const publicMemberMultiWorksFixture: PublicMemberProfile = {
  ...publicMemberFixture,
  works: [publicWorkCardFixture, publicWorkCardFixture2],
}

export const publicMemberNoWorksFixture: PublicMemberProfile = {
  ...publicMemberFixture,
  works: [],
}

export const publicMemberNoContributionsFixture: PublicMemberProfile = {
  ...publicMemberFixture,
  contributions: [],
}

export const publicWorkFixture: WorkPublic = {
  slug: workCardFixture.slug,
  title: workCardFixture.title,
  summary: workCardFixture.summary,
  cover_media_id: null,
  tags: workCardFixture.tags,
  external_links: [{ label: 'Repository', url: 'https://github.com/example/embodied' }],
  content: workContentFixture,
  author: {
    member_id: memberMeFixture.member_id,
    display_name: 'Ada Lovelace',
    picture_media_id: null,
  },
  published_at: workCardFixture.published_at as string,
  updated_at: workCardFixture.updated_at,
}

// --- Certifications ---------------------------------------------------------

export const certificationCardFixture: CertificationCard = {
  id: 'cert-1',
  status: 'submitted',
  active: true,
  work: { id: workCardFixture.id, title: workCardFixture.title, slug: workCardFixture.slug },
  member: { member_id: memberMeFixture.member_id, name: 'Ada Lovelace' },
  snapshot_version: 2,
  version_reviewed: 0,
  changed_since_review: false,
  submitted_at: '2026-02-02T10:00:00Z',
  decided_at: null,
}

export const certificationDetailFixture: CertificationDetail = {
  id: certificationCardFixture.id,
  status: certificationCardFixture.status,
  active: certificationCardFixture.active,
  work: certificationCardFixture.work,
  member: certificationCardFixture.member,
  snapshot: {
    slug: workCardFixture.slug,
    title: workCardFixture.title,
    summary: workCardFixture.summary,
    cover_media_id: null,
    tags: workCardFixture.tags,
    external_links: [{ label: 'Repository', url: 'https://github.com/example/embodied' }],
    content: workContentFixture,
  },
  snapshot_version: certificationCardFixture.snapshot_version,
  version_reviewed: certificationCardFixture.version_reviewed,
  changed_since_review: certificationCardFixture.changed_since_review,
  captured_at: '2026-02-02T09:59:00Z',
  submitted_at: certificationCardFixture.submitted_at,
  decided_at: null,
  decided_by: null,
  decided_by_role: null,
  latest_feedback: null,
  decisions: [],
  created_at: '2026-02-02T09:59:00Z',
  updated_at: '2026-02-02T10:00:00Z',
  certificate: null,
}

export const certificationListFixture = (
  items: CertificationCard[] = [certificationCardFixture],
): Paginated<CertificationCard> => paginated(items)

// --- Certificates -----------------------------------------------------------

export const certificateMemberFixture: CertificateMember = {
  certificate_id: 'THL-CERT-2026-ABCDEFGHJKLM',
  request_id: certificationCardFixture.id,
  work_title: workCardFixture.title,
  work_slug: workCardFixture.slug,
  member_name: 'Ada Lovelace',
  status: 'issued',
  issued_at: '2026-02-05T12:00:00Z',
  revoked_at: null,
  revocation_reason: null,
  email_status: 'sent',
  email_sent_at: '2026-02-05T12:01:00Z',
  pdf_filename: 'THL-CERT-2026-ABCDEFGHJKLM.pdf',
  pdf_size_bytes: 20480,
  verify_url: `https://thridhalabs.test/verify-certificate/THL-CERT-2026-ABCDEFGHJKLM`,
  download_path: '/member/certificates/THL-CERT-2026-ABCDEFGHJKLM/download',
}

export const certificateAdminFixture: CertificateAdmin = {
  ...certificateMemberFixture,
  issued_by: 'Ada Lovelace',
  issued_by_role: 'admin',
  decided_at: '2026-02-05T11:59:00Z',
  template_version: '1',
  email_attempts: 1,
  email_last_error: null,
}

export const publicCertificateFixture: PublicCertificate = {
  certificate_id: certificateMemberFixture.certificate_id,
  status: 'issued',
  issued_at: certificateMemberFixture.issued_at,
  member_name: certificateMemberFixture.member_name,
  work_title: certificateMemberFixture.work_title,
  work_url: `https://thridhalabs.test/members/${memberMeFixture.member_id}/works/${workCardFixture.slug}`,
  revoked_at: null,
  revocation_reason: null,
  work: null,
}

export const publicCertificateWorkFixture: PublicCertificateWork = {
  title: workCardFixture.title,
  summary: workCardFixture.summary,
  cover_media_id: null,
  tags: workCardFixture.tags,
  external_links: [{ label: 'Repository', url: 'https://github.com/example/embodied' }],
  content: workContentFixture,
  author: {
    member_id: memberMeFixture.member_id,
    display_name: 'Ada Lovelace',
    picture_media_id: null,
  },
  member_profile_url: `https://thridhalabs.test/members/${memberMeFixture.member_id}`,
  certified_at: certificateMemberFixture.issued_at,
  current_work_url: `https://thridhalabs.test/members/${memberMeFixture.member_id}/works/${workCardFixture.slug}`,
  has_newer_version: false,
}

// --- Activities ---------------------------------------------------------------

export const publicActivityFixture: PublicActivity = {
  slug: 'ai-builders-programme-2026',
  title: 'AI Builders Programme 2026',
  activity_type: 'programme',
  summary: 'A four-week programme for applied AI builders.',
  description: 'Build, break and ship real AI systems with the lab.',
  presentation_status: 'upcoming',
  start_date: '2026-03-01',
  end_date: '2026-03-28',
  banner_media_id: null,
  featured: true,
  display_order: 0,
  roles_offered: ['Product Analyst', 'AI Engineer'],
  tags: ['AI', 'cohort'],
  has_brief: true,
  registration_open: true,
}

export const adminActivityFixture: AdminActivity = {
  id: 'a-1',
  title: publicActivityFixture.title,
  slug: publicActivityFixture.slug,
  activity_type: 'programme',
  summary: publicActivityFixture.summary,
  description: publicActivityFixture.description,
  status: 'published',
  presentation_status: 'upcoming',
  start_date: publicActivityFixture.start_date,
  end_date: publicActivityFixture.end_date,
  banner_media_id: null,
  featured: true,
  display_order: 0,
  roles_offered: publicActivityFixture.roles_offered,
  tags: publicActivityFixture.tags,
  brief: { version: 1, filename: 'brief.pdf', size_bytes: 2048, uploaded_at: '2026-02-01T00:00:00Z' },
  brief_history_count: 1,
  cancel_reason: null,
  participant_counts: { invited: 0, confirmed: 1 },
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-02-01T00:00:00Z',
  published_at: '2026-02-01T00:00:00Z',
  cancelled_at: null,
  archived_at: null,
}

export const publicActivitiesFixture = (): Paginated<PublicActivity> =>
  paginated([publicActivityFixture])

export const adminActivitiesFixture = (): Paginated<AdminActivity> =>
  paginated([adminActivityFixture])

export const memberActivityFixture: MemberActivity = {
  slug: publicActivityFixture.slug,
  title: publicActivityFixture.title,
  activity_type: 'programme',
  summary: publicActivityFixture.summary,
  presentation_status: 'upcoming',
  start_date: publicActivityFixture.start_date,
  end_date: publicActivityFixture.end_date,
  banner_media_id: null,
  has_brief: true,
  registration_open: true,
  can_register: true,
  can_withdraw: false,
  participation_status: null,
  participation_role: null,
}

export const activityParticipantsFixture = (): Paginated<ActivityParticipant> =>
  paginated([
    {
      id: 'part-1',
      activity_id: adminActivityFixture.id,
      member_id: memberMeFixture.id,
      member_readable_id: memberMeFixture.member_id,
      member_name: 'Ada Lovelace',
      member_email: memberMeFixture.email,
      role: 'AI Engineer',
      status: 'confirmed',
      source: 'self_registered',
      note: null,
      invited_at: null,
      responded_at: '2026-02-02T00:00:00Z',
      confirmed_at: '2026-02-03T00:00:00Z',
      withdrawn_at: null,
      email_sent_at: null,
      created_at: '2026-02-02T00:00:00Z',
      updated_at: '2026-02-03T00:00:00Z',
    },
  ])

// --- Progress reports ---------------------------------------------------------

/** A project activity the member is a confirmed participant of. */
export const reportProjectFixture: MemberProjectSummary = {
  activity_id: 'a-project-1',
  slug: 'embodied-agents',
  title: 'Embodied Agents',
  role: 'AI Engineer',
  presentation_status: 'ongoing',
  start_date: '2026-01-05',
  end_date: '2026-06-30',
  banner_media_id: null,
  report_count: 3,
  pending_count: 1,
  changes_requested_count: 1,
  approved_count: 1,
  last_report_at: '2026-02-10T10:00:00Z',
}

export const memberProjectsFixture = (): {
  items: MemberProjectSummary[]
} => ({ items: [reportProjectFixture] })

export const memberReportFixture: MemberReport = {
  id: 'r-1',
  activity_id: reportProjectFixture.activity_id,
  activity_slug: reportProjectFixture.slug,
  activity_title: reportProjectFixture.title,
  role: reportProjectFixture.role,
  description: 'Shipped the first end-to-end training loop and recorded the baselines.',
  evidence_links: ['https://github.com/example/embodied'],
  status: 'pending',
  version: 1,
  editable: true,
  submitted_at: '2026-02-10T10:00:00Z',
  updated_at: '2026-02-10T10:00:00Z',
  reviewed_at: null,
  review_feedback: null,
  review_history: [],
}

export const changesRequestedReportFixture: MemberReport = {
  ...memberReportFixture,
  id: 'r-2',
  description: 'Iterating on the gripper controller.',
  status: 'changes_requested',
  editable: true,
  reviewed_at: '2026-02-08T09:00:00Z',
  review_feedback: 'Please link the run log you mentioned.',
  review_history: [
    {
      status: 'changes_requested',
      reviewer_name: 'owner@thridhalabs.com',
      feedback: 'Please link the run log you mentioned.',
      version: 0,
      decided_at: '2026-02-08T09:00:00Z',
    },
  ],
}

export const approvedReportFixture: MemberReport = {
  ...memberReportFixture,
  id: 'r-3',
  description: 'Completed the sensor-fusion milestone.',
  status: 'approved',
  version: 0,
  editable: false,
  reviewed_at: '2026-02-05T14:00:00Z',
  review_feedback: null,
  review_history: [
    {
      status: 'approved',
      reviewer_name: 'owner@thridhalabs.com',
      feedback: null,
      version: 0,
      decided_at: '2026-02-05T14:00:00Z',
    },
  ],
}

export const reportListFixture = (items: MemberReport[] = [memberReportFixture]): Paginated<MemberReport> =>
  paginated(items)

export const adminReportFixture: AdminReport = {
  id: memberReportFixture.id,
  activity_id: memberReportFixture.activity_id,
  activity_slug: memberReportFixture.activity_slug,
  activity_title: memberReportFixture.activity_title,
  member_id: memberMeFixture.id,
  member_readable_id: memberMeFixture.member_id,
  member_name: memberMeFixture.full_name ?? memberMeFixture.email,
  member_email: memberMeFixture.email,
  role: memberReportFixture.role,
  description: memberReportFixture.description,
  evidence_links: memberReportFixture.evidence_links,
  status: memberReportFixture.status,
  version: memberReportFixture.version,
  submitted_at: memberReportFixture.submitted_at,
  updated_at: memberReportFixture.updated_at,
  reviewed_at: null,
  reviewed_by: null,
  review_feedback: null,
  review_history: [],
}

export const adminReportListFixture = (
  items: AdminReport[] = [adminReportFixture],
): Paginated<AdminReport> => paginated(items)

export const contributionHistoryFixture: ContributionHistory = {
  total_reports: 1,
  items: [
    {
      activity_id: reportProjectFixture.activity_id,
      slug: reportProjectFixture.slug,
      title: reportProjectFixture.title,
      role: reportProjectFixture.role,
      report_count: 1,
      reports: [
        {
          id: 'r-3',
          description: approvedReportFixture.description,
          evidence_links: [],
          approved_at: '2026-02-05T14:00:00Z',
          submitted_at: '2026-02-04T10:00:00Z',
        },
      ],
      summaries: [],
    },
  ],
}

export const aiSourceOverviewFixture: AiSourceOverviewResponse = {
  projects: [
    {
      activity_id: 'act-1',
      slug: 'atlas-engine',
      title: 'Atlas Engine',
      approved_count: 2,
      members: [
        {
          member_id: 'member-1',
          member_readable_id: 'THL-M-2026-0001',
          member_name: 'Ada Lovelace',
          approved_count: 2,
          summary_id: null,
          summary_state: null,
        },
      ],
    },
    {
      activity_id: 'act-2',
      slug: 'beacon-app',
      title: 'Beacon App',
      approved_count: 1,
      members: [
        {
          member_id: 'member-2',
          member_readable_id: 'THL-M-2026-0002',
          member_name: 'Grace Hopper',
          approved_count: 1,
          summary_id: null,
          summary_state: null,
        },
      ],
    },
  ],
}

export const aiSummaryFixture = (
  overrides: Partial<AiSummaryAdminResponse> = {},
): AiSummaryAdminResponse => ({
  id: 'sum-1',
  activity_id: 'act-1',
  activity_slug: 'atlas-engine',
  activity_title: 'Atlas Engine',
  member_id: 'member-1',
  member_readable_id: 'THL-M-2026-0001',
  member_name: 'Ada Lovelace',
  state: 'draft',
  draft_content: 'Generated draft summary.',
  draft_model: 'openai/gpt-oss-120b',
  draft_generated_at: '2026-02-06T10:00:00Z',
  draft_reviewed: false,
  draft_outdated: false,
  published_content: null,
  published_model: null,
  published_at: null,
  source_reports: [
    { report_id: 'r-1', version: 1, submitted_at: '2026-02-04T10:00:00Z' },
  ],
  source_report_count: 1,
  outdated: false,
  last_error_code: null,
  last_error_message: null,
  generations: [],
  updated_at: '2026-02-06T10:00:00Z',
  ...overrides,
})

export const aiSummaryListFixture = (
  items: AiSummaryAdminResponse[] = [aiSummaryFixture()],
): AiSummaryListResponse => ({
  items,
  total: items.length,
  page: 1,
  page_size: 20,
  pages: items.length > 0 ? 1 : 0,
})
