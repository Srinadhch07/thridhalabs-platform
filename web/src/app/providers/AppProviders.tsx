/** Global provider composition for the application. */

import type { ReactNode } from 'react'
import { AuthProvider } from './AuthProvider'
import { BrandingProvider } from './BrandingProvider'
import { CareersProvider } from './CareersProvider'
import { SiteSettingsProvider } from './SiteSettingsProvider'

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <BrandingProvider>
        <SiteSettingsProvider>
          <CareersProvider>{children}</CareersProvider>
        </SiteSettingsProvider>
      </BrandingProvider>
    </AuthProvider>
  )
}