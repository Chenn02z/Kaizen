import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Served by FastAPI under /miniapp, so assets must resolve under that prefix.
// In dev, /me is proxied to the local FastAPI server.
export default defineConfig({
  base: '/miniapp/',
  plugins: [react()],
  server: {
    proxy: {
      '/me': 'http://localhost:8000',
    },
  },
})
