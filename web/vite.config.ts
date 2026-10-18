import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In development, forward /api to Django so the app behaves as a single origin,
// matching production (Django serves the built app). Session auth + CSRF depend on this.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/admin': 'http://localhost:8000',
    },
  },
})
