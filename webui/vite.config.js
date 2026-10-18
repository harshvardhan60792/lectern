import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' so the built files load from any folder (the desktop window serves them locally).
// In development, /api calls go to the Python test server: python -m app --browser --no-open
export default defineConfig({
  base: './',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:8765' },
  },
  build: { chunkSizeWarningLimit: 900 },
})
