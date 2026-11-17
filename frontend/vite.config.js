import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Em dev, /api vai para o FastAPI. No build, o React vai para backend/static
// e é servido pelo próprio FastAPI (um app só na ShardCloud).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: { '/api': process.env.VITE_PROXY_TARGET || 'http://localhost:8000' },
  },
  build: { outDir: '../backend/static', emptyOutDir: true },
})
