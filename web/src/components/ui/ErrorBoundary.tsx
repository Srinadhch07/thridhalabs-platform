/**
 * Lightweight React error boundary — a crash renders a safe fallback instead of
 * a blank page. Stack traces are logged in development only and never shown.
 */

import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'
import { env } from '../../app/config/env'

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
}

interface ErrorBoundaryState {
  error: Error | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    if (env.isDev) {
      // Development-only diagnostics; never surfaced to users.
      console.error('[ErrorBoundary]', error, info.componentStack)
    }
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        this.props.fallback ?? (
          <div className="state-card state-card--error" role="alert">
            <p className="eyebrow">Application error</p>
            <h2 className="state-card__title">Something went wrong</h2>
            <p className="state-card__body">
              An unexpected error occurred. Please reload the page to continue.
            </p>
          </div>
        )
      )
    }
    return this.props.children
  }
}