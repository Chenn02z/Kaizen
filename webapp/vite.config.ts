import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Served by FastAPI under /miniapp, so assets must resolve under that prefix.
// In dev, dashboard API requests are proxied to the local FastAPI server.
export default defineConfig({
  base: '/miniapp/',
  plugins: [react()],
  server: {
    proxy: {
      '/dashboard': 'http://localhost:8000',
    },
  },
})
