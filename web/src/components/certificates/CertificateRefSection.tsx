/** CertificateRefSection — loads the full certificate referenced by a
 * certification detail and renders its summary in the given scope. */

import { useAdminCertificate, useMemberCertificate } from '../../features/certificates/hooks'
import { CertificateSummary } from './CertificateSummary'
import { InlineLoader } from '../ui/InlineLoader'
import { ErrorState } from '../ui/ErrorState'
import type { CertificateRef } from '../../types/certificate'

export function CertificateRefSection({
  certificate,
  scope,
}: {
  certificate: CertificateRef
  scope: 'admin' | 'member'
}) {
  const adminResult = useAdminCertificate(scope === 'admin' ? certificate.certificate_id : undefined)
  const memberResult = useMemberCertificate(scope === 'member' ? certificate.certificate_id : undefined)
  const { data, loading, error, reload } = scope === 'admin' ? adminResult : memberResult

  return (
    <section className="cert-detail__section" aria-label="Certificate">
      <h2 className="cert-detail__section-title">Certificate</h2>
      {loading ? <InlineLoader label="Loading certificate…" /> : null}
      {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}
      {data ? <CertificateSummary certificate={data} scope={scope} /> : null}
    </section>
  )
}
