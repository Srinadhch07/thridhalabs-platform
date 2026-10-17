/** Site settings — the public response is the presentation subset. */

export interface GeneralSettings {
  site_name: string
  tagline: string
  description: string
}

export interface ContactSettings {
  contact_email: string | null
  contact_phone: string | null
  whatsapp: string | null
  address: string | null
}

export interface SocialSettings {
  urls: Record<string, string>
}

export interface FooterSettings {
  copyright_text: string
}

export interface SeoSettings {
  seo_title: string
  seo_description: string
  seo_keywords: string[]
}

export interface PublicSiteSettings {
  general: GeneralSettings
  contact: ContactSettings
  social: SocialSettings
  footer: FooterSettings
  seo: SeoSettings
  /** Plain boolean system state (not a secret) driving the public
  maintenance gate. */
  maintenance_mode: boolean
}

export interface AdminSiteSettings extends PublicSiteSettings {
  id: string
  analytics: {
    google_verification: string | null
    google_analytics: string | null
  }
  maintenance_mode: boolean
  created_at: string
  updated_at: string
}