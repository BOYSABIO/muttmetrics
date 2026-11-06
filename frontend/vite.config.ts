import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv, type ProxyOptions } from 'vite'

const frontendDir = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(frontendDir, '..')
const appVersion = JSON.parse(
  fs.readFileSync(path.join(frontendDir, 'package.json'), 'utf8'),
).version as string

/** Match API reject_insecure_api_key (#187) — proxy must not forward a toy key. */
const MIN_API_KEY_LENGTH = 24
const INSECURE_API_KEYS = new Set(['dev-change-me'])

/**
 * Read API_KEY from the repo-root .env (or the process env). Never use a VITE_
 * name — those get compiled into the SPA bundle (#194).
 */
function requireApiKey(mode: string): string {
  const fromRoot = loadEnv(mode, repoRoot, '')
  const key = (fromRoot.API_KEY || process.env.API_KEY || '').trim()
  if (!key || INSECURE_API_KEYS.has(key) || key.length < MIN_API_KEY_LENGTH) {
    throw new Error(
      'API_KEY is missing or insecure for the Vite /api proxy (#194). ' +
        'Set API_KEY in the repo-root .env (≥24 chars, not `dev-change-me`). ' +
        'Generate: python -c "import secrets; print(secrets.token_urlsafe(32))" ' +
        'then restart `npm run dev` / `npm run preview`.',
    )
  }
  return key
}

function apiProxy(apiKey: string): Record<string, ProxyOptions> {
  return {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
      rewrite: (p) => p.replace(/^\/api/, ''),
      configure: (proxy) => {
        proxy.on('proxyReq', (proxyReq) => {
          proxyReq.setHeader('X-API-Key', apiKey)
        })
      },
    },
  }
}

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  // Build does not need the key (SPA never embeds it). Dev/preview proxy does.
  const proxy =
    command === 'serve' ? apiProxy(requireApiKey(mode)) : undefined

  return {
    plugins: [react()],
    // Bake package.json version into the SPA so a phone screenshot shows the build (#197).
    define: {
      'import.meta.env.VITE_APP_VERSION': JSON.stringify(appVersion),
    },

    // npm run dev: maintainer only, hot reload, this PC only
    server: {
      host: '127.0.0.1',
      port: 5173,
      strictPort: true,
      proxy,
    },

    // npm run build, then npm run preview: local checks + the e2e smoke, this PC only.
    // The groomer uses the home server (Caddy + tailscale serve, #93), not this.
    preview: {
      host: '127.0.0.1',
      port: 5174,
      strictPort: true,
      proxy,
    },
  }
})
