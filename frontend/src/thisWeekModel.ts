/**
 * Display logic for the This week screen (0.6.5).
 *
 * Every rate still comes from the API (SQL, ADR-003, MIN_N). This module only
 * formats numbers, compares two periods the API already returned, and picks
 * what to say about them. No metric is computed here.
 */

import type {
  EurPerHourCell,
  MetricValue,
  PeriodSummary,
  UtilizationDay,
  UtilizationWeek,
} from './api'
import { addDays, formatWeekday, mondayOf, parseISODate, toISODate } from './dates'

// ---------------------------------------------------------------------------
// Numbers
// ---------------------------------------------------------------------------

export function formatMoney(n: number): string {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  }).format(n)
}

/** "11h", "2.5h", "45 min". */
export function formatHours(minutes: number): string {
  if (minutes > 0 && minutes < 60) return `${minutes} min`
  const h = minutes / 60
  return `${Number(h.toFixed(h >= 10 ? 0 : 1))}h`
}

/** "4h" for the day cap. */
export function formatCap(minutes: number): string {
  return `${Number((minutes / 60).toFixed(1))}h`
}

// ---------------------------------------------------------------------------
// This period vs the previous one
// ---------------------------------------------------------------------------

export type Delta = {
  /** "€48", "2", "1.5h" (the arrow carries the direction), or "same" */
  text: string
  dir: 'up' | 'down' | 'same'
}

function dirOf(n: number): Delta['dir'] {
  return n > 0 ? 'up' : n < 0 ? 'down' : 'same'
}

export type SummaryDeltas = {
  takeHome: Delta
  grooms: Delta
  hours: Delta
  eurPerHour: Delta | null
}

/** null when the previous period had no grooms: "+€343 vs nothing" says nothing. */
export function summaryDeltas(
  cur: PeriodSummary,
  prev: PeriodSummary | null | undefined,
): SummaryDeltas | null {
  if (!prev || prev.visit_count === 0) return null
  const money = Math.round(cur.revenue_inc_tip - prev.revenue_inc_tip)
  const grooms = cur.visit_count - prev.visit_count
  const hours = (cur.groomed_minutes - prev.groomed_minutes) / 60
  const hoursRounded = Number(Math.abs(hours).toFixed(1))
  const a = cur.eur_per_hour_inc_tip.value
  const b = prev.eur_per_hour_inc_tip.value
  const rate = a !== null && b !== null ? Math.round(a - b) : null
  const delta = (n: number, text: string): Delta =>
    n === 0 ? { text: 'same', dir: 'same' } : { text, dir: dirOf(n) }
  return {
    takeHome: delta(money, formatMoney(Math.abs(money))),
    grooms: delta(grooms, String(Math.abs(grooms))),
    hours: delta(hoursRounded === 0 ? 0 : hours, `${hoursRounded}h`),
    eurPerHour: rate === null ? null : delta(rate, formatMoney(Math.abs(rate))),
  }
}

/** "vs last week", or "vs last week at this point" while the week is running. */
export function comparisonLabel(mode: 'week' | 'month', partial: boolean): string {
  return `vs last ${mode}${partial ? ' at this point' : ''}`
}

// ---------------------------------------------------------------------------
// Coat rows
// ---------------------------------------------------------------------------

export function coatLabel(score: number, shaved: boolean): string {
  const base = score === 0 ? 'Worst' : score === 5 ? 'Best' : `Coat ${score}`
  return shaved ? `${base} · shaved` : base
}

export function sortCoatCells(cells: EurPerHourCell[]): EurPerHourCell[] {
  return cells
    .slice()
    .sort(
      (a, b) =>
        a.condition_score - b.condition_score ||
        Number(a.shaved_down) - Number(b.shaved_down),
    )
}

/** One plain sentence about the coat rows that have a rate. */
export function coatInsight(cells: EurPerHourCell[], minN: number, days: number): string {
  const ready = cells.filter((c) => c.eur_per_hour_inc_tip.value !== null)
  if (ready.length === 0) {
    return `Each coat score needs ${minN} grooms in ${days} days before it shows a rate.`
  }
  // Rounded like the rows show them, so the sentence matches the numbers below it.
  const rate = (c: EurPerHourCell) => Math.round(c.eur_per_hour_inc_tip.value as number)
  if (ready.length === 1) {
    const c = ready[0]
    return `${coatLabel(c.condition_score, c.shaved_down)} earns ${formatMoney(rate(c))} an hour. The other coats are still filling up.`
  }
  const best = ready.reduce((x, y) => (rate(y) > rate(x) ? y : x))
  const worst = ready.reduce((x, y) => (rate(y) < rate(x) ? y : x))
  const gap = rate(best) - rate(worst)
  if (gap === 0) return 'Every coat with enough grooms earns about the same per hour.'
  return `${coatLabel(best.condition_score, best.shaved_down)} earns ${formatMoney(gap)} an hour more than ${coatLabel(worst.condition_score, worst.shaved_down)}.`
}

// ---------------------------------------------------------------------------
// Day strip
// ---------------------------------------------------------------------------

export type StripColumn = {
  key: string
  label: string
  minutes: number
  grooms: number
  /** Days in this column that went over the cap (on actual time). */
  overDays: number
  isToday: boolean
  isFuture: boolean
}

/** Mon–Sun, including days without grooms, so the week reads left to right. */
export function weekColumns(
  start: string,
  days: UtilizationDay[],
  capMinutes: number,
  today: string,
): StripColumn[] {
  const byDate = new Map(days.map((d) => [d.visit_date, d]))
  return Array.from({ length: 7 }, (_, i) => {
    const iso = toISODate(addDays(parseISODate(start), i))
    const d = byDate.get(iso)
    const minutes = d?.actual_minutes ?? 0
    return {
      key: iso,
      label: formatWeekday(iso).slice(0, 2),
      minutes,
      grooms: d?.n ?? 0,
      overDays: minutes > capMinutes ? 1 : 0,
      isToday: iso === today,
      isFuture: iso > today,
    }
  })
}

/**
 * Every Monday-based week of the month (clipped to it), grooms and minutes from
 * the API's weekly rows (#178), and days over the cap counted from daily rows.
 */
export function monthColumns(
  start: string,
  end: string,
  weeks: UtilizationWeek[],
  days: UtilizationDay[],
  capMinutes: number,
  today: string,
): StripColumn[] {
  const byWeek = new Map(weeks.map((w) => [w.week_start, w]))
  const cols: StripColumn[] = []
  for (let monday = mondayOf(parseISODate(start)); toISODate(monday) <= end; monday = addDays(monday, 7)) {
    const weekStart = toISODate(monday)
    const from = weekStart < start ? start : weekStart
    const sunday = toISODate(addDays(monday, 6))
    const to = sunday > end ? end : sunday
    const w = byWeek.get(weekStart)
    cols.push({
      key: weekStart,
      label: String(parseISODate(from).getDate()),
      minutes: w?.actual_minutes ?? 0,
      grooms: w?.n ?? 0,
      overDays: days.filter(
        (d) => d.visit_date >= from && d.visit_date <= to && d.actual_minutes > capMinutes,
      ).length,
      isToday: from <= today && today <= to,
      isFuture: from > today,
    })
  }
  return cols
}

// ---------------------------------------------------------------------------
// Milestones (all-time grooms)
// ---------------------------------------------------------------------------

const MILESTONES = [10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]

export type Milestone = { previous: number; next: number; toGo: number; progress: number }

export function nextMilestone(count: number): Milestone {
  const next = MILESTONES.find((m) => m > count) ?? (Math.floor(count / 10000) + 1) * 10000
  const idx = MILESTONES.indexOf(next)
  const previous = idx > 0 ? MILESTONES[idx - 1] : idx === 0 ? 0 : next - 10000
  return {
    previous,
    next,
    toGo: next - count,
    progress: Math.min(1, Math.max(0, (count - previous) / (next - previous))),
  }
}

// ---------------------------------------------------------------------------
// Small-sample copy
// ---------------------------------------------------------------------------

/** "€42" or null while under MIN_N. */
export function rateText(mv: MetricValue): string | null {
  return mv.value === null ? null : formatMoney(mv.value)
}
