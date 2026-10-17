/// <reference types="vite/client" />

// The env vars the SPA reads (frontend/.env, see .env.example). Typing them
// turns a misspelled name into a compile error instead of a silent undefined.
interface ImportMetaEnv {
  /** Same value as API_KEY in the root .env. Compiled into the bundle: see privacy.md. */
  readonly VITE_API_KEY: string
  /** Optional salon name shown in the header. Empty or missing: app name only. */
  readonly VITE_BUSINESS_NAME?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
