import { useState } from 'react'
import { useAiSettings, useAiSettingsActions } from '../../../features/ai/hooks/useAi'
import { SaveButton } from '../../../components/form/SaveButton'
import { FormField } from '../../../components/form/FormField'
import { TextInput } from '../../../components/form/TextInput'
import { ErrorState } from '../../../components/ui/ErrorState'
import { ContentSkeleton } from '../../../components/ui/ContentSkeleton'
import { getErrorMessage } from '../../../lib/errors/ApiError'

export default function AdminAiSettingsPage() {
  const { data: settings, loading, error, reload } = useAiSettings()
  const { test, save, remove, testing, saving, removing, lastTest, lastError } = useAiSettingsActions()
  const [apiKey, setApiKey] = useState('')
  const [showRemove, setShowRemove] = useState(false)

  const encryptionConfigured = settings?.encryption_available !== false

  const handleTest = async () => {
    const key = apiKey.trim()
    if (!key) return
    await test(key)
  }

  const handleSave = async () => {
    const key = apiKey.trim()
    if (!key) return
    await save(key)
    setApiKey('')
    await reload()
  }

  const handleRemove = async () => {
    if (!showRemove) {
      setShowRemove(true)
      return
    }
    await remove()
    setShowRemove(false)
    await reload()
  }

  const effectiveError = error ? getErrorMessage(error) : lastError

  return (
    <div className="admin-page">
      <header className="admin-page__header">
        <div className="admin-page__header-main">
          <h1 className="admin-page__title">AI Settings</h1>
          <p className="admin-page__desc">
            Secure Groq API key management. Keys are encrypted at rest and never returned to the browser.
          </p>
        </div>
      </header>

      {loading ? <ContentSkeleton rows={3} /> : null}
      {error && !loading ? <ErrorState error={error} onRetry={reload} /> : null}

      {settings && !loading && (
        <div className="member-stack">
          <div className="member-card">
            <h3 className="member-card__title">Configuration</h3>
            <dl className="form-list">
              <div className="form-list__item">
                <dt>Provider</dt>
                <dd>{settings.provider}</dd>
              </div>
              <div className="form-list__item">
                <dt>Model</dt>
                <dd>{settings.model}</dd>
              </div>
              <div className="form-list__item">
                <dt>Configured</dt>
                <dd>{settings.configured ? 'Yes' : 'No'}</dd>
              </div>
              <div className="form-list__item">
                <dt>Encryption configured</dt>
                <dd>{encryptionConfigured ? 'Yes' : 'No'}</dd>
              </div>
              <div className="form-list__item">
                <dt>Key hint</dt>
                <dd>{settings.key_hint || '—'}</dd>
              </div>
              {settings.key_set_at && (
                <div className="form-list__item">
                  <dt>Key set at</dt>
                  <dd>{new Date(settings.key_set_at).toLocaleString()}</dd>
                </div>
              )}
              {settings.last_test_at && (
                <div className="form-list__item">
                  <dt>Last test</dt>
                  <dd>
                    {settings.last_test_ok ? 'OK' : 'Failed'} — {new Date(settings.last_test_at).toLocaleString()}
                    {settings.last_test_error ? ` (${settings.last_test_error})` : ''}
                  </dd>
                </div>
              )}
            </dl>
            {!encryptionConfigured && (
              <p className="member-card__desc" style={{ color: 'var(--color-warning)' }}>
                Encryption not configured on the server. AI settings cannot be saved until AI_SETTINGS_ENCRYPTION_KEY is configured.
              </p>
            )}
          </div>

          <div className="member-card">
            <h3 className="member-card__title">API Key</h3>
            <FormField id="ai-api-key" label="Groq API Key (input not prefilled)">
              <TextInput
                id="ai-api-key"
                type="password"
                value={apiKey}
                onChange={(value) => setApiKey(value)}
                placeholder="Enter new Groq API key"
                autoComplete="off"
              />
            </FormField>
            <div className="form-actions">
              <button
                type="button"
                className="btn btn--ghost"
                onClick={handleTest}
                disabled={testing || !apiKey.trim() || !encryptionConfigured}
              >
                {testing ? 'Testing...' : 'Test connection'}
              </button>
              <SaveButton
                busy={saving}
                disabled={saving || !apiKey.trim() || !encryptionConfigured}
                onClick={handleSave}
                type="button"
              >
                {saving ? 'Saving...' : settings.configured ? 'Replace key' : 'Save key'}
              </SaveButton>
              {settings.configured && (
                <button
                  type="button"
                  className="btn btn--danger"
                  onClick={handleRemove}
                  disabled={removing}
                >
                  {showRemove ? (removing ? 'Removing...' : 'Confirm remove') : 'Remove key'}
                </button>
              )}
            </div>
            {(lastTest || effectiveError) && (
              <div className="member-card__desc">
                {lastTest?.ok && <span style={{ color: 'var(--color-success)' }}>Test OK</span>}
                {lastTest && !lastTest.ok && (
                  <span style={{ color: 'var(--color-danger)' }}>
                    {lastTest.error_message || 'Test failed'}
                  </span>
                )}
                {effectiveError && !lastTest && (
                  <span style={{ color: 'var(--color-danger)' }}>{effectiveError}</span>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}