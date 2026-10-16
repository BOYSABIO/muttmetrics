/**
 * Salon name shown in the header and the browser tab.
 *
 * Set VITE_BUSINESS_NAME in frontend/.env (gitignored), never in code, so the
 * real business name stays out of the public repo. For demo footage, set a
 * made-up name. Restart `npm run dev` after changing it: Vite reads .env once.
 */
export const APP_NAME = 'MuttMetrics'

export const BUSINESS_NAME: string = String(
  import.meta.env.VITE_BUSINESS_NAME ?? '',
).trim()

export const PAGE_TITLE =
  BUSINESS_NAME === '' ? APP_NAME : `${BUSINESS_NAME} · ${APP_NAME}`
