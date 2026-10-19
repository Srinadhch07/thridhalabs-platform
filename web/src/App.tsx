import { AppProviders } from './app/providers/AppProviders'
import { AppRouter } from './app/router/AppRouter'
import { ScrollToTop } from './components/layout/ScrollToTop'

export default function App() {
  return (
    <AppProviders>
      <ScrollToTop />
      <AppRouter />
    </AppProviders>
  )
}