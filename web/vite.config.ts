import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// Dev server runs on 5173 (matches CORS_ORIGINS in the root .env).
// /api is proxied to the FastAPI backend so the app is same-origin in dev.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: false,
      },
      '/sitemap.xml': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: false,
      },
      '/robots.txt': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: false,
      },
      '/share': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: false,
      },
    },
  },
  preview: {
    port: 4173,
    strictPort: true,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: false,
    env: {
      // A non-localhost canonical origin so SEO helpers emit canonical/OG URLs
      // in tests, mirroring a configured production build.
      VITE_SITE_URL: 'https://thridhalabs.test',
    },
  },
})