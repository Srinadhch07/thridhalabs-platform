/** Branding theme data from the branding API. */

export type BrandingMode = 'light' | 'dark'

export interface BrandingColors {
  primary: string
  secondary: string
  accent: string
  background: string
  text: string
}

export interface BrandingMediaRefs {
  logo: string | null
  logo_dark: string | null
  logo_light: string | null
  favicon: string | null
  og_image: string | null
}

export interface PublicBranding {
  colors: BrandingColors
  mode: BrandingMode
  media: BrandingMediaRefs
}

export interface AdminBranding extends PublicBranding {
  /** Optional identifier of the active theme preset. `null` for custom palettes. */
  theme_preset: string | null
  id: string
  created_at: string
  updated_at: string
}