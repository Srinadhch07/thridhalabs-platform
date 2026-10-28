import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { ErrorBoundary } from './components/ui/ErrorBoundary'
import './styles/tokens.css'
import './styles/globals.css'
import './styles/public.css'
import './styles/admin.css'
import './styles/member.css'
import './styles/works.css'
import './styles/activities.css'
import './styles/reports.css'
import './styles/workspaces.css'

const container = document.getElementById('root')
if (!container) {
  throw new Error('Root container #root is missing from index.html')
}

createRoot(container).render(
  <StrictMode>
    <BrowserRouter>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </BrowserRouter>
  </StrictMode>,
)