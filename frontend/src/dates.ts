/**
 * Date helpers shared by the screens (#180).
 *
 * The API speaks `YYYY-MM-DD` calendar dates with no time zone. These helpers
 * build and read them in the browser's local time, never via `toISOString()`,
 * which converts to UTC and can shift the day around midnight.
 */

/** Local calendar date → "YYYY-MM-DD". */
export function toISODate(d: Date): string {
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

/** "YYYY-MM-DD" → local midnight of that day. */
export function parseISODate(s: string): Date {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function todayISODate(): string {
  return toISODate(new Date())
}

/** The Monday on or before `d` (weeks run Monday–Sunday). */
export function mondayOf(d: Date): Date {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const day = x.getDay()
  const offset = day === 0 ? -6 : 1 - day
  x.setDate(x.getDate() + offset)
  return x
}

export function firstOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1)
}

export function lastOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0)
}

export function addDays(d: Date, days: number): Date {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  x.setDate(x.getDate() + days)
  return x
}

/** The 1st of the month `months` away from `d`'s month. */
export function addMonths(d: Date, months: number): Date {
  return new Date(d.getFullYear(), d.getMonth() + months, 1)
}

// ---------------------------------------------------------------------------
// Labels
// ---------------------------------------------------------------------------

function shortMonth(d: Date): string {
  return d.toLocaleDateString(undefined, { month: 'short' }).replace(/\.$/, '')
}

/** "Oct 12" */
export function formatShortDate(iso: string): string {
  return parseISODate(iso).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })
}

/** "Mon" */
export function formatWeekday(iso: string): string {
  return parseISODate(iso).toLocaleDateString(undefined, { weekday: 'short' })
}

/**
 * "Oct 12–18", or "Sep 28–Oct 4" across a month. Built by hand (not
 * toLocaleDateString's day/month order) so the label is never longer than
 * 13 characters: the switcher has a fixed width and must not resize.
 */
export function formatWeekRange(startIso: string, endIso: string): string {
  const start = parseISODate(startIso)
  const end = parseISODate(endIso)
  if (start.getMonth() === end.getMonth()) {
    return `${shortMonth(start)} ${start.getDate()}–${end.getDate()}`
  }
  return `${shortMonth(start)} ${start.getDate()}–${shortMonth(end)} ${end.getDate()}`
}

/** "Apr 1–30": fits the same 13ch capsule as week ranges. */
export function formatMonthRange(startIso: string, endIso: string): string {
  const start = parseISODate(startIso)
  const end = parseISODate(endIso)
  return `${shortMonth(start)} ${start.getDate()}–${end.getDate()}`
}

/** "October 2026" */
export function formatMonthTitle(isoFirst: string): string {
  return parseISODate(isoFirst).toLocaleDateString(undefined, {
    month: 'long',
    year: 'numeric',
  })
}

/** "Today", "Yesterday", "3 days ago", "5 wk ago", then "Mar 2026". */
export function formatLastVisit(iso: string | null): string {
  if (iso === null) return '—'
  const then = parseISODate(iso)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const days = Math.round((today.getTime() - then.getTime()) / 86_400_000)
  if (days <= 0) return 'Today'
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days} days ago`
  if (days < 60) return `${Math.round(days / 7)} wk ago`
  return then.toLocaleDateString(undefined, { month: 'short', year: 'numeric' })
}
