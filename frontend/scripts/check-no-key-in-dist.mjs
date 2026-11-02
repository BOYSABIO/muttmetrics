/**
 * Fail if the configured API_KEY appears anywhere under frontend/dist (#194).
 *
 * Usage (from frontend/):
 *   API_KEY=… npm run check:no-key-in-dist
 *
 * CI runs this after `npm run build`. Locally, set API_KEY to the same value
 * as the repo-root .env (the script does not load dotenv).
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendDir = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const distDir = path.join(frontendDir, 'dist')
const key = (process.env.API_KEY || '').trim()

if (!key) {
  console.error('check-no-key-in-dist: set API_KEY in the environment.')
  process.exit(1)
}

if (!fs.existsSync(distDir)) {
  console.error('check-no-key-in-dist: frontend/dist missing — run npm run build first.')
  process.exit(1)
}

const hits = []

function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      walk(full)
      continue
    }
    const text = fs.readFileSync(full, 'utf8')
    if (text.includes(key)) {
      hits.push(path.relative(frontendDir, full))
    }
  }
}

walk(distDir)

if (hits.length > 0) {
  console.error(
    'check-no-key-in-dist: API_KEY found in the SPA bundle (must stay server-side only):\n' +
      hits.map((h) => `  - ${h}`).join('\n'),
  )
  process.exit(1)
}

console.log('OK: API_KEY not present in frontend/dist (#194).')
