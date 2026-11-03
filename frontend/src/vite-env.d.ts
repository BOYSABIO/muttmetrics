/// <reference types="vite/client" />

// The env vars the SPA reads (frontend/.env, see .env.example). Typing them
// turns a misspelled name into a compile error instead of a silent undefined.
// API_KEY is NOT listed here — it must never be a VITE_ var (#194).
interface ImportMetaEnv {
  /** From package.json at build time (#197). Not a secret. */
  readonly VITE_APP_VERSION: string
  /** Optional salon name shown in the header. Empty or missing: app name only. */
  readonly VITE_BUSINESS_NAME?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
