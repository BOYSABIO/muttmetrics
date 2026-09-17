import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Where Vite forwards /api/* requests: FastAPI on this PC only (#82)
const apiProxy = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
    rewrite: (path: string) => path.replace(/^\/api/, ''),
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  // npm run dev: maintainer only, hot reload, this PC only
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: apiProxy,
  },

  // npm run build, then npm run preview: what the groomer opens over Tailscale
  preview: {
    host: '0.0.0.0',
    port: 5174,
    strictPort: true,
    proxy: apiProxy,
  },
})
